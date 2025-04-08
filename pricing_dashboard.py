import pandas as pd
import streamlit as st
import matplotlib.pyplot as plt
import seaborn as sns

st.set_page_config(page_title="Multifamily Pricing Dashboard", layout="wide")

st.title("📈 Multifamily Pricing Recommendation Dashboard")

# --- Upload Section ---
uploaded_file = st.file_uploader("Upload Yardi Rent Roll (CSV or Excel format)", type=["csv", "xlsx"])

if uploaded_file:
    # Determine file type and load accordingly
    if uploaded_file.name.endswith(".csv"):
        df = pd.read_csv(uploaded_file)
    else:
        df = pd.read_excel(uploaded_file)

    # Ensure numeric columns are properly converted
    for col in ["VacantDays", "Leads", "Tours", "CurrentRent"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

    # --- Required Columns Check ---
    required_cols = ["Unit", "FloorPlan", "Bedrooms", "VacantDays", "CurrentRent", "Leads", "Tours"]
    missing_cols = [col for col in required_cols if col not in df.columns]

    if missing_cols:
        st.error(f"Missing required columns: {', '.join(missing_cols)}")
    else:
        # --- Core Pricing Algorithm ---
        def recommend_rent(row):
            vacant_days = row["VacantDays"]
            leads = row["Leads"]
            tours = row["Tours"]
            current_rent = row["CurrentRent"]

            demand_score = (leads * 0.4 + tours * 0.6) / max(1, vacant_days)

            if demand_score < 0.3 and vacant_days > 10:
                change_pct = -0.02  # Decrease 2%
            elif demand_score > 0.8:
                change_pct = 0.01  # Increase 1%
            else:
                change_pct = 0.0

            new_rent = round(current_rent * (1 + change_pct))
            return pd.Series([new_rent, change_pct])

        df[["RecommendedRent", "ChangePercent"]] = df.apply(recommend_rent, axis=1)

        # --- Display Floor Plan Summary ---
        st.subheader("Summary by Floor Plan")
        summary = df.groupby(["Bedrooms", "FloorPlan"]).agg(
            AvgCurrentRent=("CurrentRent", "mean"),
            AvgRecommendedRent=("RecommendedRent", "mean"),
            Units=("Unit", "count")
        )
        summary["SuggestedChange%"] = ((summary["AvgRecommendedRent"] - summary["AvgCurrentRent"]) / summary["AvgCurrentRent"] * 100).round(2)

        st.dataframe(summary.reset_index())

        # --- Filter Section ---
        st.sidebar.header("Filter Units")
        selected_bedrooms = st.sidebar.multiselect("Select Bedrooms", options=df["Bedrooms"].unique(), default=df["Bedrooms"].unique())
        selected_floorplans = st.sidebar.multiselect("Select Floor Plans", options=df["FloorPlan"].unique(), default=df["FloorPlan"].unique())

        filtered_df = df[(df["Bedrooms"].isin(selected_bedrooms)) & (df["FloorPlan"].isin(selected_floorplans))]

        # --- Display Unit-Level Table ---
        st.subheader("Unit-Level Recommendations")
        df_display = filtered_df[["Unit", "FloorPlan", "Bedrooms", "VacantDays", "Leads", "Tours", "CurrentRent", "RecommendedRent", "ChangePercent"]].copy()
        df_display["ChangePercent"] = (df_display["ChangePercent"] * 100).round(2).astype(str) + "%"

        st.dataframe(df_display)

        # --- Charts ---
        st.subheader("📊 Visual Insights")

        col1, col2 = st.columns(2)

        with col1:
            st.markdown("**Average Rent by Floor Plan**")
            fig1, ax1 = plt.subplots()
            sns.barplot(data=summary.reset_index(), x="FloorPlan", y="AvgRecommendedRent", ax=ax1)
            ax1.set_ylabel("Recommended Rent")
            st.pyplot(fig1)

        with col2:
            st.markdown("**Vacant Days vs. Change %**")
            fig2, ax2 = plt.subplots()
            sns.scatterplot(data=filtered_df, x="VacantDays", y="ChangePercent", hue="Bedrooms", ax=ax2)
            ax2.set_ylabel("Change Percent")
            st.pyplot(fig2)

        # --- Export Button ---
        st.download_button(
            label="📂 Download Recommendations (CSV)",
            data=filtered_df.to_csv(index=False).encode("utf-8"),
            file_name="rent_recommendations.csv",
            mime="text/csv"
        )
else:
    st.info("Please upload a CSV or Excel rent roll to get started.")

"""
Evan Dunn
CS 230
This Program compares Bluebike data from the Boston area in Winter and summer and seeks to compare ridership between
the two seasons aswell as look at how rider age compares to trip length and what stations are busiest dependant on the season.
This is done uising histograms, bar charts, and an interactable map
References
https://docs.streamlit.io
https://deckgl.readthedocs.io/en/latest/
Data : https://s3.amazonaws.com/hubway-data/index.html
"""

import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import pydeck as pdk

st.set_page_config(page_title="Blue Bikes Boston", layout="wide")

def get_data():
    df_jan = pd.read_csv("201501-hubway-tripdata_4.csv")
    df_jul = pd.read_csv("201507-hubway-tripdata.csv")

    def prep_data(df, season):
        #[FUnC2P]
        df = df.copy()
        df["season"] = season
        #[COLUMnS]
        df["dur_min"] = df["tripduration"] / 60
        df["birth year"] = pd.to_numeric(df["birth year"], errors="coerce")
        df["age"] = df["birth year"].apply(lambda x: 2015 -x if pd.notna(x) else np.nan)
        #LAMBDA
        df = df[df["dur_min"] <=180]
        return df
    df_winter = prep_data(df_jan, "Winter")
    df_summer = prep_data(df_jul, "Summer")
    return df_summer, df_winter, pd.concat([df_winter, df_summer], ignore_index=True)
df_summer, df_winter, df_both = get_data()

def season_sum(df):
    return len(df), round(df["dur_min"].mean(), 1)
#FUnCRETURn2
def top_stations(df, season, n=10):
    filtered = df[df["season"] == season]
    #Filter 1 cndition
    return(filtered.groupby("start station name")
    .size()
    .reset_index(name="trips")
    .sort_values("trips", ascending=False)  #Sort
    .head(n))
#SIDEBAR BELOW
with st.sidebar:
    st.write("Blue Bikes Boston")
    season_selection = st.selectbox("Season", ["Summer", "Winter", "Both"], index=2)
    user_types = st.multiselect("Rider Type", ["Subscriber", "Customer"],
                                default=["Subscriber", "Customer"])
    top_n = st.slider("Top N Stations", 5, 25, 10)
    age_min, age_max = st.slider("Rider Age Range", 16, 90, (18, 70))
#Tabs for site
tab1, tab2, tab3, tab4 = st.tabs(["Overview", "Stations", "Demographics", "Map"])

#Overview Tab
with tab1:
    winter_trips, winter_avg = season_sum(df_winter)
    summer_trips, summer_avg = season_sum(df_summer)
    column1, column2, column3, column4 = st.columns(4)
    column1.metric("Winter Trips", f"{winter_trips:,}")
    column2.metric("Summer Trips", f"{summer_trips:,}", delta=f"+{summer_trips - winter_trips:,}")
    column3.metric("Winter Avg Duration", f"{winter_avg} min")
    column4.metric("Summer Avg Duration", f"{summer_avg} min", delta=f"+{round(summer_avg - winter_avg, 1)} min")

    st.write(f"️ Summer sees {summer_trips // winter_trips}× more trips than winter, "
            f"with rides averaging {round(summer_avg - winter_avg, 1)} minutes longer.")
    #pivot table
    st.subheader("Avg Trip Duration by Rider Type & Season")
    pivot = df_both.pivot_table(
        values="dur_min", index="usertype", columns="season", aggfunc="mean").round(1)
    #Chart 2
    st.subheader("Trip Duration")
    fig, ax = plt.subplots(figsize=(10, 4))
    bins = np.linspace(0, 90, 46)
    ax.hist(df_winter["dur_min"], bins=bins, alpha=0.75, label="Winter")
    ax.hist(df_summer["dur_min"], bins=bins, alpha=0.55, label="Summer")
    ax.set_xlabel("Trip Duration in Minutes")
    ax.set_ylabel("Number of Trips")
    ax.set_title("How Long Are Rides?  Winter vs. Summer", fontweight="bold")
    ax.legend()
    ax.spines[["top", "right"]].set_visible(False)
    st.pyplot(fig)
    plt.close()
#Station Tab
#Contains Chart 1
with tab2:
    season_choices =(["Winter", "Summer"] if season_selection == "Both" else [season_selection])
    for season in season_choices:
        station_df = top_stations(df_both, season, n=top_n) #Function call #1
        fig, ax = plt.subplots(figsize=(10, max(4, top_n * 0.38)))
        bars = ax.barh(station_df["start station name"], station_df["trips"],#graph1
                     edgecolor="white", height=0.65)
        for bar in bars:
            ax.text(bar.get_width() + station_df["trips"].max() * 0.01,
                    bar.get_y() + bar.get_height() / 2,
                    f"{int(bar.get_width()):,}", va="center", ha="left", fontsize=8.5)
        ax.invert_yaxis()
        ax.set_xlabel("Number of Departures")
        ax.set_title(f"Top {top_n} Departure Stations — {'Winter' if 'Winter' in season else ' Summer'}", fontweight="bold")
        ax.spines[["top", "right", "left"]].set_visible(False)
        ax.set_xlim(0, station_df["trips"].max() * 1.15)
        st.pyplot(fig)
        plt.close()
    busiest = df_both.groupby("start station name").size().idxmax()
    busiest_count = df_both.groupby("start station name").size().max() #maxmin
    st.write(f" Busiest station overall: {busiest} with {busiest_count:,}total departures.")
#Demographics Tab
with tab3:
    #Filter by age and rider type
    demographic_df = df_both[(df_both["age"] >= age_min) & (df_both["age"] <= age_max) &
        (df_both["usertype"].isin(user_types or ["Subscriber", "Customer"]))]
    if season_selection != "Both":
        demographic_df = demographic_df[demographic_df["season"] == season_selection]
    bins_age   = [16, 20, 25, 30, 35, 40, 45, 50, 55, 60, 65, 70, 80, 90]
    labels_age = ["16-19","20-24","25-29","30-34","35-39","40-44","45-49","50-54","55-59","60-64","65-69","70-79","80-90"]
    demographic_df["age_group"] = pd.cut(demographic_df["age"], bins=bins_age, labels=labels_age, right=False)
    age_avg = (demographic_df.groupby(["age_group", "season"], observed=True)["dur_min"]
           .mean().reset_index())

    st.subheader("Trip duration by age group and season")
    fig, ax = plt.subplots(figsize=(12, 5))
    seasons_present = age_avg["season"].unique()
    x = np.arange(len(labels_age))
    width = 0.38 if len(seasons_present) == 2 else 0.55
    for i, season in enumerate(seasons_present):
        subset = age_avg[age_avg["season"] == season].set_index("age_group")
        vals   = [subset.loc[g, "dur_min"] if g in subset.index else 0 for g in labels_age]
        offset = (i - 0.5) * width if len(seasons_present) == 2 else 0
        ax.bar(x + offset, vals, width=width, label=season,
               edgecolor="white", alpha=0.88)
    ax.set_xticks(x)
    ax.set_xticklabels(labels_age, rotation=30, ha="right", fontsize=9)
    ax.set_ylabel("Avg Trip Duration in mins")
    ax.set_xlabel("Age Group")
    ax.set_title("Avg Trip Duration by Age Group & Season")
    ax.legend()
    ax.spines[["top", "right"]].set_visible(False)
    st.pyplot(fig)
    plt.close()
#map tab
with tab4:
    map_season = st.selectbox("Map Season", ["Winter", "Summer"], key="map")
    map_stations = top_stations(df_both, map_season, n=100)  #FUnCCALL2 second time called

    coordinates_df = (df_both.groupby("start station name")
                [["start station latitude", "start station longitude"]]
                .first().reset_index())
    map_df = (map_stations
              .merge(coordinates_df, on="start station name", how="left")
              .dropna()
              .rename(columns={"start station latitude": "lat",
                               "start station longitude": "lon"}))

    max_trips = map_df["trips"].max()
    map_df["radius"] = map_df["trips"].apply(lambda t: 30 + (t / max_trips) * 300)

    map_df["tooltip"] = map_df.apply(
        lambda r: f"{r['start station name']}: {int(r['trips']):,} trips", axis=1)

    #MAP using scatter plot layer
    st.pydeck_chart(pdk.Deck(
        layers=[pdk.Layer("ScatterplotLayer", data=map_df,
                          get_position="[lon, lat]", get_radius="radius",
                        pickable=True, opacity=0.8,
                          stroked=True, get_line_color=[255, 255, 255],
                          line_width_min_pixels=1)],
        initial_view_state=pdk.ViewState(latitude=42.370, longitude=-71.095, zoom=12),
        tooltip={"text": "{tooltip}"},
        map_style="https://basemaps.cartocdn.com/gl/positron-gl-style/style.json",
    ))


    display_df = map_df[["start station name", "trips", "lat", "lon"]].copy()
    display_df.columns = ["Station", "Trips", "Latitude", "Longitude"]
    st.dataframe(display_df.sort_values("Trips", ascending=False).reset_index(drop=True),
                 use_container_width=True, height=300)
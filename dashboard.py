import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np
from shapely.geometry import MultiPoint
import geopy.distance as geodesic
import plotly.graph_objects as go


# Title of the App
st.title("Side-by-Side Comparison: Old vs New Clusters")

# Upload Excel files
old_clusters_file = st.file_uploader("Upload Old Clusters File", type=["xlsx"])
new_clusters_file = st.file_uploader("Upload New Clusters File", type=["xlsx"])

if old_clusters_file and new_clusters_file:
    # Load data from Excel files into Pandas DataFrames
    old_df = pd.read_excel(old_clusters_file)
    new_df = pd.read_excel(new_clusters_file)

    # Ensure required columns are available
    if all(col in old_df.columns for col in ['Latitude', 'Longitude', 'District', 'Cluster Name', 'Tot Population', 'Distance', 'Cost']) and \
       all(col in new_df.columns for col in ['Village Latitude', 'Village Longitude', 'District', 'Cluster Name', 'Tot Population', 'Distance', 'Cost']):

        # Dropdown for selecting a district
        selected_district = st.selectbox("Select District", old_df['District'].unique())

        # Filter the data based on the selected district
        old_filtered_df = old_df[old_df['District'] == selected_district]
        new_filtered_df = new_df[new_df['District'] == selected_district]

        # --- Global Table with Totals Across All Districts ---
        st.subheader("Global Comparison: All Districts Summary")
        all_districts_old_summary = old_df.groupby('District').agg({
            'Cluster Name': 'nunique',  # Number of unique clusters
            'Tot Population': 'sum',  # Total population
            'Distance': 'mean',  # Average distance
            'Cost': 'sum'  # Total cost
        }).reset_index()

        all_districts_new_summary = new_df.groupby('District').agg({
            'Cluster Name': 'nunique',
            'Tot Population': 'sum',
            'Distance': 'mean',
            'Cost': 'sum'
        }).reset_index()

        combined_summary = pd.merge(all_districts_old_summary, all_districts_new_summary, on='District', suffixes=('_Old', '_New'))
        st.dataframe(combined_summary)

        # --- Dynamic Table for Selected District ---
        st.subheader(f"Analysis for {selected_district}")

        def summary_stats(df):
            return {
                'Total Clusters': df['Cluster Name'].nunique(),
                'Total Population': df['Tot Population'].sum(),
                'Avg Distance': df['Distance'].mean(),
                'Total Cost': df['Cost'].sum()
            }

        old_summary = summary_stats(old_filtered_df)
        new_summary = summary_stats(new_filtered_df)

        comparison_table = pd.DataFrame({
            'Metric': ['Total Clusters', 'Total Population', 'Avg Distance', 'Total Cost'],
            'Old Clusters': [old_summary['Total Clusters'], old_summary['Total Population'], old_summary['Avg Distance'], old_summary['Total Cost']],
            'New Clusters': [new_summary['Total Clusters'], new_summary['Total Population'], new_summary['Avg Distance'], new_summary['Total Cost']]
        })

        st.table(comparison_table)

        # --- Bar Chart Comparison: Population per Cluster (Old vs New) ---
        st.subheader(f"Comparison: Population per Cluster in {selected_district}")
        col1, col2 = st.columns(2)

        with col1:
            st.write("**Old Clusters**")
            bar_chart_data_old = old_filtered_df.groupby('Cluster Name')['Tot Population'].sum().reset_index()
            fig_bar_old = px.bar(bar_chart_data_old, x='Cluster Name', y='Tot Population', title="Total Population per Cluster (Old Clusters)")
            st.plotly_chart(fig_bar_old)

        with col2:
            st.write("**New Clusters**")
            bar_chart_data_new = new_filtered_df.groupby('Cluster Name')['Tot Population'].sum().reset_index()
            fig_bar_new = px.bar(bar_chart_data_new, x='Cluster Name', y='Tot Population', title="Total Population per Cluster (New Clusters)")
            st.plotly_chart(fig_bar_new)

        # --- Combined Line Graph: Distance Comparison ---
        st.subheader("Combined Distance Comparison: Old vs New Clusters")

        # Add 'Type' column to differentiate between old and new clusters
        old_filtered_df['Type'] = 'Old Clusters'
        new_filtered_df['Type'] = 'New Clusters'

        # Combine both DataFrames for easy comparison
        combined_df = pd.concat([old_filtered_df[['Cluster Name', 'Distance', 'Type']],
                                 new_filtered_df[['Cluster Name', 'Distance', 'Type']]])

        fig_combined = px.line(combined_df, x='Cluster Name', y='Distance', color='Type',
                               title="Distance Comparison: Old vs New Clusters")
        st.plotly_chart(fig_combined)

        # --- Geo Map Comparison with Cluster Areas (Grouped Villages by Cluster Name) ---
        st.subheader(f"Geo Map: Cluster Mapping in {selected_district}")
        col1, col2 = st.columns([1, 1])

        def draw_convex_hull(latitudes, longitudes):
            points = MultiPoint([(lon, lat) for lat, lon in zip(latitudes, longitudes)])
            hull = points.convex_hull
            if hull.geom_type == 'Polygon':
                hull_coords = hull.exterior.coords.xy
            else:
                hull_coords = [[], []]  # Return empty if no polygon is created
            return list(hull_coords[1]), list(hull_coords[0]) # Return latitudes and longitudes

        # --- Old Clusters Map ---
        with col1:
            st.write("**Old Clusters**")
            fig_old_map = go.Figure()

            # Add markers and boundaries for Old Clusters
            for cluster_name, group in old_filtered_df.groupby('Cluster Name'):
                latitudes = group['Latitude'].values
                longitudes = group['Longitude'].values

                # Draw convex hull boundary around the cluster of villages
                hull_latitudes, hull_longitudes = draw_convex_hull(latitudes, longitudes)

                if hull_latitudes:  # If we have enough points to create a boundary
                    fig_old_map.add_trace(go.Scattermapbox(
                        lat=hull_latitudes,
                        lon=hull_longitudes,
                        mode='lines',
                        line=dict(width=2, color='rgba(0, 255, 0, 1)'),  # Green for old clusters
                        showlegend=False
                    ))

                # Add village points inside the cluster
                fig_old_map.add_trace(go.Scattermapbox(
                    lat=latitudes,
                    lon=longitudes,
                    mode='markers',
                    marker=dict(size=7, color='blue'),
                    text=group['Cluster Name'],  # Tooltip with cluster name
                    showlegend=False
                ))

            fig_old_map.update_layout(
                mapbox_style="open-street-map",
                mapbox_zoom=6,
                mapbox_center={"lat": old_filtered_df['Latitude'].mean(), "lon": old_filtered_df['Longitude'].mean()},
                height=600  # Vertically larger map
            )
            st.plotly_chart(fig_old_map)

        # --- New Clusters Map ---
        with col2:
            st.write("**New Clusters**")
            fig_new_map = go.Figure()

            # Add markers and boundaries for New Clusters
            for cluster_name, group in new_filtered_df.groupby('Cluster Name'):
                latitudes = group['Village Latitude'].values
                longitudes = group['Village Longitude'].values

                # Draw convex hull boundary around the cluster of villages
                hull_latitudes, hull_longitudes = draw_convex_hull(latitudes, longitudes)

                if hull_latitudes:  # If we have enough points to create a boundary
                    fig_new_map.add_trace(go.Scattermapbox(
                        lat=hull_latitudes,
                        lon=hull_longitudes,
                        mode='lines',
                        line=dict(width=2, color='rgba(0, 0, 255, 1)'),  # Blue for new clusters
                        showlegend=False
                    ))

                # Add village points inside the cluster
                fig_new_map.add_trace(go.Scattermapbox(
                    lat=latitudes,
                    lon=longitudes,
                    mode='markers',
                    marker=dict(size=7, color='red'),
                    text=group['Cluster Name'],  # Tooltip with cluster name
                    showlegend=False
                ))

            fig_new_map.update_layout(
                mapbox_style="open-street-map",
                mapbox_zoom=6,
                mapbox_center={"lat": new_filtered_df['Village Latitude'].mean(), "lon": new_filtered_df['Village Longitude'].mean()},
                height=600  # Vertically larger map
            )
            st.plotly_chart(fig_new_map)


    else:
        st.error("Missing required latitude/longitude columns in one of the uploaded files.")
else:
    st.warning("Please upload both Old and New Clusters Excel files.")

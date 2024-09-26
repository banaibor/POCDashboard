from fastapi import FastAPI, UploadFile, File
from fastapi.responses import JSONResponse
import pandas as pd
import numpy as np

app = FastAPI()

@app.post("/upload/")
async def upload_files(old_clusters: UploadFile = File(...), new_clusters: UploadFile = File(...)):
    # Read old clusters file
    old_df = pd.read_excel(old_clusters.file)
    
    # Read new clusters file
    new_df = pd.read_excel(new_clusters.file)
    
    # Ensure 'District' is in both DataFrames
    if 'District' not in old_df.columns or 'District' not in new_df.columns:
        return JSONResponse(status_code=400, content={"error": "District column is missing in one of the files."})

    # Aggregate old clusters data by District
    old_agg = old_df.groupby('District').agg({
        'Tot Population': 'sum',
        'Cost': 'sum',
        'Distance': 'mean'  # Calculate average distance
    }).reset_index().rename(columns={
        'Tot Population': 'Old Total Population', 
        'Cost': 'Old Total Cost',
        'Distance': 'Old Average Distance'
    })

    # Aggregate new clusters data by District
    new_agg = new_df.groupby('District').agg({
        'Tot Population': 'sum',
        'Cost': 'sum',
        'Distance': 'mean'  # Calculate average distance
    }).reset_index().rename(columns={
        'Tot Population': 'New Total Population', 
        'Cost': 'New Total Cost',
        'Distance': 'New Average Distance'
    })

    # Merge the two aggregated DataFrames on 'District'
    merged_df = pd.merge(old_agg, new_agg, on='District', how='outer')

    # Fill NaN values with 0 for comparison
    merged_df.fillna(0, inplace=True)

    # Prepare comparison data
    comparison_data = []
    for _, row in merged_df.iterrows():
        comparison_data.append({
            'District': row['District'],
            'Old Total Population': int(row['Old Total Population']),  # Convert to int
            'New Total Population': int(row['New Total Population']),  # Convert to int
            'Old Total Cost': float(row['Old Total Cost']),           # Convert to float
            'New Total Cost': float(row['New Total Cost']),           # Convert to float
            'Population Improvement': int(row['New Total Population']) - int(row['Old Total Population']),
            'Cost Reduction': float(row['Old Total Cost']) - float(row['New Total Cost']),
            'Old Average Distance': float(row['Old Average Distance']),  # Convert to float
            'New Average Distance': float(row['New Average Distance'])   # Convert to float
        })

    # Count unique clusters
    total_old_clusters = old_df['Cluster Name'].nunique()
    total_new_clusters = new_df['Cluster Name'].nunique()

    # Analyze far away distances (updated threshold of 40 km)
    far_away_threshold = 40
    far_away_old = old_df[old_df['Distance'] > far_away_threshold]
    far_away_new = new_df[new_df['Distance'] > far_away_threshold]

    # Prepare analysis for far away clusters
    far_away_analysis = {
        "Far Away Old Clusters": len(far_away_old),
        "Far Away New Clusters": len(far_away_new)
    }

    # Check if any comparison data exists
    if not comparison_data:
        return JSONResponse(status_code=400, content={"error": "No matching records found between old and new clusters."})

    # Prepare cluster analysis
    cluster_analysis = {
        "Total Old Districts": old_agg['District'].nunique(),
        "Total New Districts": new_agg['District'].nunique(),
        "Total Old Population": int(old_agg['Old Total Population'].sum()),  # Convert to int
        "Total New Population": int(new_agg['New Total Population'].sum()),  # Convert to int
        "Total Old Cost": float(old_agg['Old Total Cost'].sum()),           # Convert to float
        "Total New Cost": float(new_agg['New Total Cost'].sum()),           # Convert to float
        "Total Old Clusters": total_old_clusters,
        "Total New Clusters": total_new_clusters,
        **far_away_analysis  # Include far away cluster analysis
    }

    return JSONResponse(content={"comparison_data": comparison_data, "cluster_analysis": cluster_analysis})
import pandas as pd
import os
from pathlib import Path
import numpy as np
import joblib
import json
from sklearn.model_selection import TimeSeriesSplit
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.metrics import mean_absolute_error, r2_score

# Optional visualization imports
try:
    import matplotlib.pyplot as plt
    import seaborn as sns
    HAS_MATPLOTLIB = True
except ImportError:
    HAS_MATPLOTLIB = False

# --- Data Access and Loading ---
# Define the base path to the shelter data using local folder
BASE_DIR = Path(__file__).parent
base_data_path = BASE_DIR / 'Data'

# Construct full paths to each CSV file using the exact filenames found
df_occupancy_path = base_data_path / 'Daily Shelter & Overnight Service Occupancy & Capacity' / 'Daily shelter overnight occupancy.csv'
df_flow_path = base_data_path / 'Toronto Shelter System Flow' / 'toronto-shelter-system-flow.csv'
df_intake_path = base_data_path / 'Central Intake calls' / 'Central Intake Call Wrap-Up Codes Data.csv'

# Load all available weather files and concatenate
weather_files = [
    base_data_path / 'Daily Data Report Toronto City Weather' / 'en_climate_daily_ON_6158355_2021_P1D.csv',
    base_data_path / 'Daily Data Report Toronto City Weather' / 'en_climate_daily_ON_6158355_2022_P1D.csv',
    base_data_path / 'Daily Data Report Toronto City Weather' / 'en_climate_daily_ON_6158355_2023_P1D.csv',
    base_data_path / 'Daily Data Report Toronto City Weather' / 'en_climate_daily_ON_6158355_2024_P1D.csv',
    base_data_path / 'Daily Data Report Toronto City Weather' / 'en_climate_daily_ON_6158355_2025_P1D.csv'
]

weather_dfs = []
for file in weather_files:
    try:
        weather_dfs.append(pd.read_csv(str(file)))
    except FileNotFoundError:
        print(f"Warning: Weather file not found: {file}")
df_weather = pd.concat(weather_dfs, ignore_index=True)

# Load other dataframes
df_occupancy = pd.read_csv(str(df_occupancy_path))
df_flow = pd.read_csv(str(df_flow_path))
df_intake = pd.read_csv(str(df_intake_path))

# --- Data Merging and Preprocessing ---
# 1. Convert and rename date columns to 'DATE'
df_occupancy['OCCUPANCY_DATE'] = pd.to_datetime(df_occupancy['OCCUPANCY_DATE'])
df_occupancy = df_occupancy.rename(columns={'OCCUPANCY_DATE': 'DATE'})

df_intake['Date'] = pd.to_datetime(df_intake['Date'])
df_intake = df_intake.rename(columns={'Date': 'DATE'})

df_weather['Date/Time'] = pd.to_datetime(df_weather['Date/Time'])
df_weather = df_weather.rename(columns={'Date/Time': 'DATE'})

# 2. Convert and rename df_flow date column to 'DATE' (first day of month)
df_flow['DATE'] = pd.to_datetime(df_flow['date(mmm-yy)'], format='%b-%y').dt.to_period('M').dt.start_time
df_flow = df_flow.drop(columns=['date(mmm-yy)'])

# 3. Group df_occupancy by 'DATE' and 'SECTOR' and sum 'SERVICE_USER_COUNT'
df_occupancy_daily_sector = df_occupancy.groupby(['DATE', 'SECTOR'])['SERVICE_USER_COUNT'].sum().reset_index()

# 4. Group df_intake by 'DATE' and sum relevant columns
df_intake_daily = df_intake.groupby('DATE')[['Total calls handled', 'Code 3A - Shelter Space Unavailable - Family', 'Code 3B - Shelter Space Unavailable - Individuals/Couples']].sum().reset_index()

# Refine df_flow to be monthly totals, assuming 'All Population' is most relevant
df_flow_all_pop = df_flow[df_flow['population_group'] == 'All Population'].copy()
df_flow_all_pop.drop(columns=['population_group'], inplace=True)

# 5. Left merge df_occupancy_daily_sector with df_intake_daily on 'DATE'
merged_df = pd.merge(df_occupancy_daily_sector, df_intake_daily, on='DATE', how='left')

# 6. Left merge merged_df with df_weather on 'DATE'
merged_df = pd.merge(merged_df, df_weather, on='DATE', how='left')

# 7. Left merge current merged_df with df_flow_all_pop on 'DATE'
merged_df = pd.merge(merged_df, df_flow_all_pop, on='DATE', how='left')

# 8. Sort merged_df by the 'DATE' column in ascending order
merged_df = merged_df.sort_values(by='DATE').reset_index(drop=True)

# 9. Convert 'population_group_percentage' column to numeric BEFORE ffill
merged_df['population_group_percentage'] = merged_df['population_group_percentage'].str.replace('%', '', regex=False)
merged_df['population_group_percentage'] = pd.to_numeric(merged_df['population_group_percentage'], errors='coerce') / 100

# Identify numerical columns for ffill
flow_cols_for_ffill_from_all_pop_inclusive = [col for col in df_flow_all_pop.columns if col != 'DATE']
intake_cols_for_ffill = ['Total calls handled', 'Code 3A - Shelter Space Unavailable - Family', 'Code 3B - Shelter Space Unavailable - Individuals/Couples']
weather_numeric_cols_for_ffill = [
    'Max Temp (°C)', 'Min Temp (°C)', 'Mean Temp (°C)', 'Heat Deg Days (°C)',
    'Cool Deg Days (°C)', 'Total Precip (mm)', 'Snow on Grnd (cm)'
]

# Apply ffill to the identified columns, grouped by 'SECTOR'
for col in flow_cols_for_ffill_from_all_pop_inclusive:
    if col in merged_df.columns:
        merged_df[col] = merged_df.groupby('SECTOR')[col].ffill()

for col in intake_cols_for_ffill:
    if col in merged_df.columns:
        merged_df[col] = merged_df.groupby('SECTOR')[col].ffill()

for col in weather_numeric_cols_for_ffill:
    if col in merged_df.columns:
        merged_df[col] = merged_df.groupby('SECTOR')[col].ffill()

# Fill any remaining NaNs in numerical columns with 0
for col in intake_cols_for_ffill:
    if col in merged_df.columns:
        merged_df[col] = merged_df[col].fillna(0)

if 'Snow on Grnd (cm)' in merged_df.columns:
    merged_df['Snow on Grnd (cm)'] = merged_df['Snow on Grnd (cm)'].fillna(0)

# Drop highly sparse columns, irrelevant flag columns, and constant/redundant identifier columns
columns_to_drop = [
    'Data Quality', 'Max Temp Flag', 'Min Temp Flag', 'Mean Temp Flag',
    'Heat Deg Days Flag', 'Cool Deg Days Flag', 'Total Rain (mm)',
    'Total Rain Flag', 'Total Snow (cm)', 'Total Snow Flag', 'Total Precip Flag',
    'Snow on Grnd Flag', 'Dir of Max Gust (10s deg)', 'Spd of Max Gust (km/h)',
    'Dir of Max Gust Flag', 'Spd of Max Gust Flag',
    '_id', 'Longitude (x)', 'Latitude (y)', 'Station Name', 'Climate ID',
    'Year', 'Month', 'Day'
]
existing_columns_to_drop = [col for col in columns_to_drop if col in merged_df.columns]
merged_df.drop(columns=existing_columns_to_drop, inplace=True)

# --- Truth-Centered Feature Engineering ---
merged_df = merged_df.sort_values(by=['DATE', 'SECTOR']).reset_index(drop=True)

# Time-series lags for occupancy
merged_df['occupancy_7day_rolling_avg'] = merged_df.groupby('SECTOR')['SERVICE_USER_COUNT'].transform(lambda x: x.rolling(window=7, min_periods=1).mean())
merged_df['occupancy_30day_rolling_avg'] = merged_df.groupby('SECTOR')['SERVICE_USER_COUNT'].transform(lambda x: x.rolling(window=30, min_periods=1).mean())

# Date-based features
merged_df['day_of_week'] = merged_df['DATE'].dt.dayofweek
merged_df['day_of_month'] = merged_df['DATE'].dt.day
merged_df['month'] = merged_df['DATE'].dt.month
merged_df['year'] = merged_df['DATE'].dt.year
merged_df['week_of_year'] = merged_df['DATE'].dt.isocalendar().week.astype(int)
merged_df['day_of_year'] = merged_df['DATE'].dt.dayofyear

# Economic features (payday cycles)
merged_df['is_payday'] = ((merged_df['DATE'].dt.day == 1) | (merged_df['DATE'].dt.day == 15)).astype(int)

# Environmental features (Extreme Cold Alerts)
if 'Min Temp (°C)' in merged_df.columns:
    merged_df['extreme_cold_alert'] = (merged_df['Min Temp (°C)'] < -15).astype(int)
else:
    merged_df['extreme_cold_alert'] = 0

# Encode 'SECTOR' category
one_hot_encoded_sector = pd.get_dummies(merged_df['SECTOR'], prefix='SECTOR')
merged_df = pd.concat([merged_df, one_hot_encoded_sector], axis=1)
merged_df = merged_df.drop('SECTOR', axis=1)

# --- Define Target and Model Setup ---
merged_df['True Demand'] = merged_df['SERVICE_USER_COUNT'] + \
                          merged_df['Code 3A - Shelter Space Unavailable - Family'] + \
                          merged_df['Code 3B - Shelter Space Unavailable - Individuals/Couples']

merged_df.drop(columns=[
    'SERVICE_USER_COUNT',
    'Code 3A - Shelter Space Unavailable - Family',
    'Code 3B - Shelter Space Unavailable - Individuals/Couples'
], inplace=True)

y = merged_df['True Demand']
X = merged_df.drop(columns=['True Demand', 'DATE'])

# Store dates for plotting
dates_for_plotting = merged_df['DATE'].copy()

# --- Model Training and Validation ---
tscv = TimeSeriesSplit(n_splits=5)
mae_scores = []
r2_scores = [] # Added for R^2 scores

# To ensure 'model' is defined for the export step, we'll train it here and assign the last fold's model
model = None # Initialize model to None

# Store results for plotting
last_fold_y_val = None
last_fold_y_pred = None
last_fold_dates = None

for fold, (train_index, val_index) in enumerate(tscv.split(X)):
    X_train, X_val = X.iloc[train_index], X.iloc[val_index]
    y_train, y_val = y.iloc[train_index], y.iloc[val_index]

    current_fold_model = HistGradientBoostingRegressor(random_state=42)
    current_fold_model.fit(X_train, y_train)
    y_pred = current_fold_model.predict(X_val)

    mae = mean_absolute_error(y_val, y_pred)
    mae_scores.append(mae)

    r2 = r2_score(y_val, y_pred) # Calculate R^2 score
    r2_scores.append(r2)

    # Assign the model from the last fold for export and store validation results
    if fold == tscv.n_splits - 1:
        model = current_fold_model
        last_fold_y_val = y_val
        last_fold_y_pred = y_pred
        # Get the corresponding dates for the last validation fold
        last_fold_dates = dates_for_plotting.iloc[val_index].reset_index(drop=True)

print(f"Average Mean Absolute Error across all folds: {np.mean(mae_scores):.2f}")
print(f"Average R^2 Score across all folds: {np.mean(r2_scores):.2f}") # Print average R^2

# --- Model Export ---
model_pipeline = {
    'model': model,
    'feature_columns': X.columns.tolist(),
    'X_numeric_mean': X.select_dtypes(include=[np.number]).mean() # Save X_numeric_mean
}
joblib.dump(model_pipeline, str(BASE_DIR / 'shelter_demand_model.joblib'))
print("Model and feature columns saved successfully as 'shelter_demand_model.joblib'.")

# --- Prediction Function Development ---
# Load the saved model and feature columns (these are already in scope for this combined cell)
loaded_model_pipeline = joblib.load(str(BASE_DIR / 'shelter_demand_model.joblib'))

def get_live_prediction(date_str, sector, temp, loaded_model_pipeline):
    """
    Provides a real-time shelter demand prediction based on input date, sector, and minimum temperature.

    Args:
        date_str (str): Date in 'YYYY-MM-DD' format.
        sector (str): The shelter sector (e.g., 'Families', 'Men', 'Women', 'Youth', 'Mixed Adult').
        temp (float): Minimum temperature in Celsius for the day.
        loaded_model_pipeline (dict): The dictionary containing the loaded model, feature columns, and numeric means.

    Returns:
        str: A JSON string containing the input parameters and the predicted shelter demand.
    """
    loaded_model = loaded_model_pipeline['model']
    loaded_feature_columns = loaded_model_pipeline['feature_columns']
    loaded_X_numeric_mean = loaded_model_pipeline['X_numeric_mean']

    input_data = {}
    for col in loaded_feature_columns:
        if col.startswith('SECTOR_'):
            input_data[col] = False
        elif col in loaded_X_numeric_mean.index:
            input_data[col] = loaded_X_numeric_mean[col]
        else:
            input_data[col] = 0

    input_df = pd.DataFrame([input_data])

    date_obj = pd.to_datetime(date_str)

    input_df['Min Temp (°C)'] = temp
    input_df['Max Temp (°C)'] = temp + 5
    input_df['Mean Temp (°C)'] = temp + 2
    input_df['Heat Deg Days (°C)'] = max(0, 18 - input_df['Mean Temp (°C)'].iloc[0])
    input_df['Cool Deg Days (°C)'] = max(0, input_df['Mean Temp (°C)'].iloc[0] - 18)

    input_df['day_of_week'] = date_obj.dayofweek
    input_df['day_of_month'] = date_obj.day
    input_df['month'] = date_obj.month
    input_df['year'] = date_obj.year
    input_df['week_of_year'] = date_obj.isocalendar().week # Removed .astype(int)
    input_df['day_of_year'] = date_obj.dayofyear

    input_df['is_payday'] = int((date_obj.day == 1) | (date_obj.day == 15))

    input_df['extreme_cold_alert'] = int(input_df['Min Temp (°C)'].iloc[0] < -15)

    sector_col_name = f'SECTOR_{sector}'
    if sector_col_name in input_df.columns:
        input_df[sector_col_name] = True

    input_df = input_df[loaded_feature_columns]

    for col in input_df.columns:
        if input_df[col].dtype == 'bool':
            input_df[col] = input_df[col].astype(int)

    prediction = loaded_model.predict(input_df)[0]

    result = {
        "date": date_str,
        "sector": sector,
        "min_temp_celsius": temp,
        "predicted_shelter_demand": round(prediction)
    }
    return json.dumps(result, indent=4)

print("Prediction function `get_live_prediction` defined and ready.")

# --- Demonstrate Prediction ---
print("\n--- Demonstrating `get_live_prediction` ---")
prediction_output = get_live_prediction(date_str='2025-12-25', sector='Families', temp=-10.0, loaded_model_pipeline=loaded_model_pipeline)
print(prediction_output)

print("\nAll steps completed: data processed, model trained and evaluated, and prediction function demonstrated.")
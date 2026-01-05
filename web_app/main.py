from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, ConfigDict
from typing import Optional
import joblib
import json
from pathlib import Path
import pandas as pd
from datetime import datetime

# Initialize FastAPI app
app = FastAPI(
    title="Homeless Shelter Demand Predictor",
    description="Predicts shelter demand based on date, sector, and temperature",
    version="1.0.0"
)

# Get paths (absolute to work regardless of where app is started from)
BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"
TEMPLATES_DIR = BASE_DIR / "templates"

# Mount static files (CSS, JavaScript) with absolute path
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

# Initialize templates with absolute path
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

# Get paths to model
ROOT_DIR = Path(__file__).resolve().parent.parent
MODEL_PATH = ROOT_DIR / 'shelter_demand_model.joblib'

# Load model
try:
    loaded_model_pipeline = joblib.load(str(MODEL_PATH))
    model = loaded_model_pipeline['model']
    feature_columns = loaded_model_pipeline['feature_columns']
    X_numeric_mean = loaded_model_pipeline['X_numeric_mean']
    print("✓ Model loaded successfully")
except Exception as e:
    print(f"✗ Error loading model: {e}")
    raise

# Define request/response models
class PredictionRequest(BaseModel):
    date: str  # Format: YYYY-MM-DD
    sector: str  # One of: Families, Men, Women, Youth, Mixed Adult
    min_temp_celsius: float  # Minimum temperature in Celsius

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "date": "2025-12-25",
                "sector": "Families",
                "min_temp_celsius": -10.0
            }
        }
    )

class PredictionResponse(BaseModel):
    date: str
    sector: str
    min_temp_celsius: float
    predicted_shelter_demand: int
    status: str = "success"

class SectorInfo(BaseModel):
    sectors: list
    temperatures_range: dict
    sample_dates: list

# Helper function for prediction
def get_live_prediction(date_str: str, sector: str, temp: float) -> dict:
    """
    Provides a real-time shelter demand prediction based on input date, sector, and minimum temperature.
    
    Args:
        date_str: Date in 'YYYY-MM-DD' format
        sector: The shelter sector (e.g., 'Families', 'Men', 'Women', 'Youth', 'Mixed Adult')
        temp: Minimum temperature in Celsius for the day
    
    Returns:
        dict: Prediction result with date, sector, temperature, and predicted demand
    """
    try:
        input_data = {}
        for col in feature_columns:
            if col.startswith('SECTOR_'):
                input_data[col] = False
            elif col in X_numeric_mean.index:
                input_data[col] = X_numeric_mean[col]
            else:
                input_data[col] = 0

        input_df = pd.DataFrame([input_data])
        date_obj = pd.to_datetime(date_str)

        # Temperature features
        input_df['Min Temp (°C)'] = temp
        input_df['Max Temp (°C)'] = temp + 5
        input_df['Mean Temp (°C)'] = temp + 2
        input_df['Heat Deg Days (°C)'] = max(0, 18 - input_df['Mean Temp (°C)'].iloc[0])
        input_df['Cool Deg Days (°C)'] = max(0, input_df['Mean Temp (°C)'].iloc[0] - 18)

        # Date features
        input_df['day_of_week'] = date_obj.dayofweek
        input_df['day_of_month'] = date_obj.day
        input_df['month'] = date_obj.month
        input_df['year'] = date_obj.year
        input_df['week_of_year'] = date_obj.isocalendar().week
        input_df['day_of_year'] = date_obj.dayofyear

        # Economic & Environmental features
        input_df['is_payday'] = int((date_obj.day == 1) | (date_obj.day == 15))
        input_df['extreme_cold_alert'] = int(temp < -15)

        # Set sector
        sector_col_name = f'SECTOR_{sector}'
        if sector_col_name in input_df.columns:
            input_df[sector_col_name] = True

        # Align with model features
        input_df = input_df[feature_columns]

        # Convert boolean to int
        for col in input_df.columns:
            if input_df[col].dtype == 'bool':
                input_df[col] = input_df[col].astype(int)

        # Make prediction
        prediction = model.predict(input_df)[0]

        return {
            "date": date_str,
            "sector": sector,
            "min_temp_celsius": temp,
            "predicted_shelter_demand": round(prediction)
        }
    
    except Exception as e:
        raise ValueError(f"Prediction error: {str(e)}")

# Routes
@app.get("/", tags=["Frontend"])
async def get_index():
    """Serve the main HTML page"""
    return FileResponse(str(BASE_DIR / "templates" / "index.html"))

@app.get("/api/info", tags=["Info"], response_model=SectorInfo)
async def get_model_info():
    """Get information about available sectors and model parameters"""
    sectors = [col.replace('SECTOR_', '') for col in feature_columns if col.startswith('SECTOR_')]
    return SectorInfo(
        sectors=sectors,
        temperatures_range={"min": -25, "max": 30, "recommended_step": 1},
        sample_dates=[
            "2025-01-15",
            "2025-06-15",
            "2025-12-25"
        ]
    )

@app.post("/api/predict", tags=["Prediction"], response_model=PredictionResponse)
async def predict(request: PredictionRequest):
    """
    Make a shelter demand prediction.
    
    Parameters:
    - date: Date in YYYY-MM-DD format
    - sector: One of Families, Men, Women, Youth, Mixed Adult
    - min_temp_celsius: Minimum temperature in Celsius
    """
    try:
        # Validate date format
        try:
            datetime.strptime(request.date, "%Y-%m-%d")
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")
        
        # Validate sector
        valid_sectors = [col.replace('SECTOR_', '') for col in feature_columns if col.startswith('SECTOR_')]
        if request.sector not in valid_sectors:
            raise HTTPException(
                status_code=400, 
                detail=f"Invalid sector. Must be one of: {', '.join(valid_sectors)}"
            )
        
        # Validate temperature
        if request.min_temp_celsius < -50 or request.min_temp_celsius > 50:
            raise HTTPException(status_code=400, detail="Temperature must be between -50 and 50 Celsius")
        
        # Make prediction
        result = get_live_prediction(request.date, request.sector, request.min_temp_celsius)
        return PredictionResponse(**result)
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Prediction error: {str(e)}")

@app.get("/api/health", tags=["Health"])
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "model_loaded": model is not None,
        "timestamp": datetime.now().isoformat()
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

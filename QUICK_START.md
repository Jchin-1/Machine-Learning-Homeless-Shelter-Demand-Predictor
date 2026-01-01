# 🚀 Quick Start Guide

## Get Started in 2 Minutes

### Step 1: Open Command Prompt
```
Press Windows + R
Type: cmd
Press Enter
```

### Step 2: Navigate to Web App
```bash
cd "c:\Users\singh\Documents\Homeless Shelter\web_app"
```

### Step 3: Start the Server
```bash
python main.py
```

You should see:
```
✓ Model loaded successfully
INFO:     Started server process
INFO:     Application startup complete
INFO:     Uvicorn running on http://0.0.0.0:8000
```

### Step 4: Open in Browser
Go to: **http://localhost:8000**

### Step 5: Make a Prediction
1. **Select a date** (e.g., today)
2. **Choose a sector** (e.g., Families)
3. **Enter temperature** (e.g., -5)
4. **Click "Get Prediction"**

Done! 🎉

---

## 📊 What You Can Do

### Prediction Examples

**Cold Winter Day**
- Date: 2025-01-15
- Sector: Families
- Temperature: -15°C
- Result: ~1,450 beds needed

**Hot Summer Day**
- Date: 2025-07-15
- Sector: Youth
- Temperature: 25°C
- Result: ~1,200 beds needed

**Payday Effect**
- Date: 2025-01-01 (payday)
- Sector: Men
- Temperature: 0°C
- Result: Higher demand

---

## 🔧 Tech Details

**Available Sectors:**
- Families
- Men
- Women
- Youth
- Mixed Adult

**Temperature Range:**
- Min: -50°C
- Max: 50°C

**Date Range:**
- Min: 2020-01-01
- Max: 2026-12-31

---

## 🆘 Troubleshooting

### Issue: Port 8000 in use
**Solution:**
```bash
python main.py --port 8001
# Then open http://localhost:8001
```

### Issue: Python not found
**Solution:**
Make sure Python is installed and in PATH:
```bash
python --version
```

### Issue: Module not found
**Solution:**
```bash
pip install -r requirements.txt
```

### Issue: Model file not found
**Solution:**
Make sure you're in the correct directory with the model file nearby.

---

## 📚 Full Documentation

See `web_app/README.md` for complete documentation

See `PROJECT_SUMMARY.md` for detailed project information

---

## 🔗 Useful Links

- **Web Interface**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs
- **Alternative Docs**: http://localhost:8000/redoc
- **Health Check**: http://localhost:8000/api/health

---

## ⏹️ Stopping the Server

Press **Ctrl + C** in the command prompt

---

**Enjoy using the Shelter Demand Predictor! 🏠**

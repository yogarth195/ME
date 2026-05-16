# ExplainHire — Installation Script for Python 3.14
# Run from inside the activated venv:
#   venv\Scripts\activate
#   .\install.ps1

Write-Host "Step 1/4: Installing main dependencies..." -ForegroundColor Cyan
pip install -r requirements.txt
if (-not $?) { Write-Host "ERROR: requirements.txt install failed" -ForegroundColor Red; exit 1 }

Write-Host "Step 2/2: Verifying Flask starts..." -ForegroundColor Cyan
python -c "import flask, anthropic, networkx, xgboost, sklearn, sentence_transformers, fitz, docx; print('All imports OK')"
if (-not $?) { Write-Host "ERROR: import check failed" -ForegroundColor Red; exit 1 }

Write-Host ""
Write-Host "All done. Run: python run.py" -ForegroundColor Green

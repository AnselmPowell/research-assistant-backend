# Complete End-to-End Backend Diagnostic Test

## Purpose
This test simulates the **ENTIRE backend pipeline** exactly as it runs in production, from the moment a user submits a research query until notes are ready to be sent to the frontend.

## What It Tests (Complete Flow)

### 📋 **Step 1: Frontend Request Simulation**
- Collects research topic and query (user input)
- Validates parameters

### 💾 **Step 2: Database Session Creation**
- Creates `ResearchSession` in database
- Sets initial status to 'initiated'

### 🤖 **Step 3: AI Services Initialization**
- Initializes LLM (Pydantic-AI with OpenAI)
- Updates session status to 'searching'

### 🔍 **Step 4: Search Term Generation**
- Uses AI to expand original query
- Generates optimized search terms

### 💡 **Step 5: Expanded Questions & Intent**
- Generates detailed research questions
- Creates explanation of user's research intent

### 📊 **Step 6: Query Embedding Creation**
- Creates semantic embedding for query
- Used for relevance detection in PDFs

### 📚 **Step 7: arXiv Paper Search**
- Searches arXiv for relevant papers
- Returns paper URLs

### 💾 **Step 8: Paper Database Records**
- Creates `Paper` objects in database
- Links papers to session
- Updates session status to 'processing'

### 🔄 **Step 9: Parallel PDF Processing**
- Downloads PDFs
- Extracts metadata with AI
- Identifies relevant pages using embeddings
- Extracts notes with LLM
- **Validates notes with threshold check**
- Creates `Note` objects in database

### ✅ **Step 10: Session Finalization**
- Updates session status to 'completed'
- Marks processing as done

### 📤 **Step 11: Frontend Response Preparation**
- Formats notes for API response
- Simulates what `/api/research/session/{id}/notes/` returns

## How to Run

```bash
cd C:\Users\anselm.powell\OneDrive - Sport Wales\Documents\Software_Engineering\ResearchAssistant\v1\backend

python test_diagnosis.py
```

## What You'll Be Asked

```
Research Topic: react programming
Specific Query (optional): useful react tip
Number of papers to test (default 3, max 5): 3
```

## What You'll See

### ✅ **Success Output:**
```
>>> STEP 9: Process PDFs in Parallel (Core Extraction)
✓ Paper 1/3: 2 notes
✓ Paper 2/3: 1 notes
✓ Paper 3/3: 0 notes

DIAGNOSTIC RESULTS
==================
Total Notes Created: 3
Notes Ready for Frontend: 3

✓ FRONTEND WOULD RECEIVE NOTES: YES
```

### ❌ **Failure Output:**
```
>>> STEP 9: Process PDFs in Parallel (Core Extraction)
✓ Paper 1/3: 0 notes
✓ Paper 2/3: 0 notes
✓ Paper 3/3: 0 notes

DIAGNOSTIC RESULTS
==================
Total Notes Created: 0
Notes Ready for Frontend: 0

✗ FRONTEND WOULD RECEIVE NOTES: NO
```

## Output Files

**`diagnostic_full_TIMESTAMP.json`** - Complete diagnostic report including:
- Test metadata (topic, query, timing)
- Pipeline statistics (papers found, processed, etc.)
- Results (notes created, frontend readiness)
- Paper-by-paper breakdown
- Sample of notes that would go to frontend
- Verdict (would frontend receive notes?)

## Interpreting Results

### 🎯 **Key Metrics:**

1. **Papers Found** - Did arXiv search work?
2. **Papers Processed** - Did PDF download work?
3. **Total Notes Created** - Did extraction work?
4. **Notes Ready for Frontend** - Did validation work?

### 🔍 **If Notes = 0:**

**Check the backend terminal for:**
```
Note FILTERED with score 0.45
Note FILTERED with score 0.38
Validation complete: 0 notes passed, 2 filtered
```

This means notes ARE being extracted but filtered out by validation threshold!

### 🔧 **Common Issues:**

| Symptom | Problem | Solution |
|---------|---------|----------|
| Papers Found = 0 | arXiv search failing | Use broader search terms |
| Papers Processed < Papers Found | PDF download errors | Check URLs in terminal |
| Notes Created = 0 (all papers) | No relevant content | Try different topic |
| Notes Created > 0, Frontend = 0 | Validation threshold too high | Lower threshold in pdf_service.py |

## Quick Fixes

### ❌ Notes filtered out (threshold too high)
**File:** `core/services/pdf_service.py` (line ~700)
```python
# Current (too strict)
threshold=0.40

# Change to (more lenient)
threshold=0.30
```

### ❌ No papers found
- Use broader search terms
- Try "machine learning" instead of "advanced transformer architectures"

### ❌ PDF download failures
- Check internet connection
- Some arXiv URLs may be invalid (older papers)

## Database Records Created

This test creates REAL database records:
- ✅ 1 `ResearchSession`
- ✅ N `Paper` objects (where N = number you specify)
- ✅ M `Note` objects (where M = successfully extracted notes)

**These can be viewed in Django admin or queried directly.**

## What This Test Reveals

✅ **If everything works:** Notes → Database → Frontend
❌ **If validation blocks:** Notes → Database → ❌ Filtered → Frontend receives 0
❌ **If extraction fails:** No notes created at all

## Example Good Output

```json
{
  "results": {
    "total_notes_created": 5,
    "notes_ready_for_frontend": 5
  },
  "verdict": {
    "would_reach_frontend": true,
    "user_would_see_notes": true
  }
}
```

## Example Bad Output (Validation Issue)

```json
{
  "results": {
    "total_notes_created": 0,
    "notes_ready_for_frontend": 0
  },
  "verdict": {
    "would_reach_frontend": false,
    "user_would_see_notes": false
  }
}
```
**Check terminal for:** `"Note FILTERED with score X.XX"`

## Next Steps After Test

1. ✅ **If notes reach frontend:** System working correctly
2. ❌ **If notes = 0:** Check terminal logs for filtering messages
3. 🔧 **Adjust threshold:** Modify `pdf_service.py` validation threshold
4. 🔄 **Re-test:** Run again with adjusted threshold
5. 📊 **Review JSON:** Check `diagnostic_full_*.json` for details

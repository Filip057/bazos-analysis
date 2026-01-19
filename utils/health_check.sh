#!/bin/bash
# Production System Health Check
# Quick status overview of continuous learning system

echo "=== Production System Health Check ==="
echo ""
echo "📁 Files:"
if [ -f "training_data_labeled.json" ]; then
    echo "  ✓ training_data_labeled.json"
else
    echo "  ✗ training_data_labeled.json missing"
fi

if [ -d "ml_models/car_ner" ]; then
    echo "  ✓ ml_models/car_ner/"
else
    echo "  ✗ ml_models/car_ner/ missing"
fi

echo ""
echo "📊 Queue Sizes:"
python3 -c "import json; print(f\"  Auto-training:  {len(json.load(open('auto_training_data.json')))} examples\")" 2>/dev/null || echo "  Auto-training:  0 examples (file not found)"
python3 -c "import json; print(f\"  Review queue:   {len(json.load(open('review_queue.json')))} cases\")" 2>/dev/null || echo "  Review queue:   0 cases (file not found)"
python3 -c "import json; print(f\"  Manual review:  {len(json.load(open('manual_review_data.json')))} corrections\")" 2>/dev/null || echo "  Manual review:  0 corrections (file not found)"

echo ""
echo "📈 Total Training Data Available:"
python3 -c "
import json, os
try:
    o = len(json.load(open('training_data_labeled.json')))
    a = len(json.load(open('auto_training_data.json'))) if os.path.exists('auto_training_data.json') else 0
    m = len(json.load(open('manual_review_data.json'))) if os.path.exists('manual_review_data.json') else 0
    total = o + a + m
    print(f\"  Total: {total} examples\")
    print(f\"    - Original:        {o} examples\")
    print(f\"    - Auto-collected:  {a} examples\")
    print(f\"    - Manual review:   {m} examples\")
    print()
    if a + m >= 300:
        print(f\"  ✓ Ready for retraining! ({a + m} new examples)\")
    else:
        print(f\"  ⚠  Need {300 - (a + m)} more examples before retraining\")
except Exception as e:
    print(f\"  ✗ Error reading training data: {e}\")
"

echo ""
echo "📅 Last Model Update:"
if [ -d "ml_models/car_ner" ]; then
    ls -lth ml_models/car_ner/ | grep -E '(meta\.json|config\.cfg)' | head -1 | awk '{print "  " $6, $7, $8, $9}'
else
    echo "  Model directory not found"
fi

echo ""
echo "🎯 Recommended Actions:"
python3 -c "
import json, os

try:
    # Check review queue
    review_count = len(json.load(open('review_queue.json'))) if os.path.exists('review_queue.json') else 0
    if review_count > 50:
        print(f\"  📝 Review {review_count} disagreements: python3 review_disagreements.py\")

    # Check if ready for retraining
    auto = len(json.load(open('auto_training_data.json'))) if os.path.exists('auto_training_data.json') else 0
    manual = len(json.load(open('manual_review_data.json'))) if os.path.exists('manual_review_data.json') else 0

    if auto + manual >= 300:
        print(f\"  🎓 Retrain model: python3 retrain_model.py --iterations 150\")

    if review_count == 0 and auto + manual < 100:
        print(f\"  🚀 Run production extraction to collect more data\")

    if review_count == 0 and auto + manual < 300:
        print(f\"  ⏳ Continue collecting data ({auto + manual}/300 for retraining)\")

except Exception:
    print(\"  ⚠  Initialize system: Run production_extractor.py first\")
"

echo ""
echo "=== End of Health Check ==="

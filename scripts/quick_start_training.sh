#!/bin/bash
# Quick Start: Incremental Training Workflow
#
# This script guides you through adding new training data to existing data

set -e

echo "========================================================================"
echo "INCREMENTAL TRAINING - QUICK START"
echo "========================================================================"
echo ""

# Check existing data
echo "📊 Checking existing training data..."
echo ""

if [ -f "training_data_labeled.json" ]; then
    count=$(python3 -c "import json; print(len(json.load(open('training_data_labeled.json'))))")
    echo "  ✅ training_data_labeled.json: $count samples"
fi

if [ -f "filtered_training_skoda.json" ]; then
    count=$(python3 -c "import json; print(len(json.load(open('filtered_training_skoda.json'))))")
    echo "  ✅ filtered_training_skoda.json: $count samples"
fi

if [ -f "training_skoda.json" ]; then
    count=$(python3 -c "import json; print(len(json.load(open('training_skoda.json'))))")
    echo "  ✅ training_skoda.json: $count samples"
fi

echo ""
echo "========================================================================"
echo "WORKFLOW:"
echo "========================================================================"
echo ""
echo "STEP 1: Export new offers"
echo "  python3 scripts/export_for_claude_labeling.py --count 300"
echo ""
echo "STEP 2: Upload to Claude chat (claude.ai)"
echo "  - Upload offers_for_labeling.json"
echo "  - Use prompt from scripts/CLAUDE_LABELING_GUIDE.md"
echo "  - Download training_data_new.json"
echo ""
echo "STEP 3: Merge with existing data"
echo "  python3 scripts/merge_training_data.py \\"
echo "    --existing training_data_labeled.json filtered_training_skoda.json \\"
echo "    --new training_data_new.json \\"
echo "    --output training_data_combined.json"
echo ""
echo "STEP 4: Train model"
echo "  python3 ml/train_model.py --input training_data_combined.json"
echo ""
echo "========================================================================"
echo ""

read -p "Do you want to export new offers now? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    read -p "How many offers? (default: 300) " count
    count=${count:-300}

    echo ""
    echo "🚀 Exporting $count offers..."
    python3 scripts/export_for_claude_labeling.py --count "$count"

    echo ""
    echo "✅ Export complete!"
    echo ""
    echo "NEXT STEPS:"
    echo "  1. Upload offers_for_labeling.json to Claude chat"
    echo "  2. Get training_data_new.json back from Claude"
    echo "  3. Run this to merge:"
    echo ""
    echo "     python3 scripts/merge_training_data.py \\"
    echo "       --existing training_data_labeled.json filtered_training_skoda.json \\"
    echo "       --new training_data_new.json \\"
    echo "       --output training_data_combined.json"
    echo ""
fi

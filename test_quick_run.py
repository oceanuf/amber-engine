#!/usr/bin/env python3
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from scripts.analyzer.daily_feature_extraction import DailyFeatureExtractor

extractor = DailyFeatureExtractor()
success = extractor.run("gold")
print("Success:", success)
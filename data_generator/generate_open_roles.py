#!/usr/bin/env python3
"""
Generate sample OpenRoles.csv data for hiring agent system.
Creates realistic job postings with role details, headcount targets, and status.
"""

import pandas as pd
import random
from datetime import datetime, timedelta

# Set random seed for reproducibility
random.seed(42)

# Define role categories and departments
roles_data = [
    {"role": "Software Engineer", "department": "Engineering", "level": "Mid", "target": 8},
    {"role": "Senior Software Engineer", "department": "Engineering", "level": "Senior", "target": 5},
    {"role": "Data Scientist", "department": "Data Science", "level": "Mid", "target": 6},
    {"role": "ML Engineer", "department": "Data Science", "level": "Senior", "target": 4},
    {"role": "Product Manager", "department": "Product", "level": "Mid", "target": 3},
    {"role": "DevOps Engineer", "department": "Engineering", "level": "Mid", "target": 4},
    {"role": "Frontend Engineer", "department": "Engineering", "level": "Mid", "target": 5},
    {"role": "Backend Engineer", "department": "Engineering", "level": "Senior", "target": 6},
    {"role": "QA Engineer", "department": "Engineering", "level": "Mid", "target": 3},
    {"role": "Engineering Manager", "department": "Engineering", "level": "Senior", "target": 2},
]

# Generate open roles data
open_roles = []

for role_info in roles_data:
    role_name = role_info["role"]
    department = role_info["department"]
    level = role_info["level"]
    target_headcount = role_info["target"]
    
    # Randomly determine filled count (0 to target-1, ensuring at least 1 open position)
    filled_count = random.randint(0, max(1, target_headcount - 1))
    open_positions = target_headcount - filled_count
    
    # Generate posting date (30-120 days ago)
    days_ago = random.randint(30, 120)
    posting_date = datetime.now() - timedelta(days=days_ago)
    
    # Determine status based on open positions
    if open_positions > 0:
        status = "Active"
    else:
        status = random.choice(["Filled", "On Hold"])
    
    # Calculate fill rate
    fill_rate = (filled_count / target_headcount * 100) if target_headcount > 0 else 0
    
    # Generate priority based on open positions and time open
    if open_positions >= target_headcount * 0.5:  # More than 50% open
        priority = "High"
    elif open_positions > 0:
        priority = "Medium"
    else:
        priority = "Low"
    
    # Add some roles that are recently posted (last 7 days)
    if random.random() < 0.2:  # 20% chance
        posting_date = datetime.now() - timedelta(days=random.randint(1, 7))
        status = "Active"
        priority = "High"
    
    open_roles.append({
        "RoleName": role_name,
        "Department": department,
        "Level": level,
        "TargetHeadcount": target_headcount,
        "FilledCount": filled_count,
        "OpenPositions": open_positions,
        "FillRate": f"{fill_rate:.1f}%",
        "PostingDate": posting_date.strftime("%Y-%m-%d"),
        "Status": status,
        "Priority": priority,
        "DaysOpen": days_ago,
    })

# Create DataFrame
df = pd.DataFrame(open_roles)

# Sort by priority and open positions (high priority first)
priority_order = {"High": 1, "Medium": 2, "Low": 3}
df["PriorityOrder"] = df["Priority"].map(priority_order)
df = df.sort_values(["PriorityOrder", "OpenPositions"], ascending=[True, False])
df = df.drop("PriorityOrder", axis=1)

# Save to CSV
output_file = "sample_inputs/OpenRoles.csv"
df.to_csv(output_file, index=False)

print(f"✅ Generated {len(open_roles)} open roles")
print(f"📁 Saved to: {output_file}")
print("\n📊 Summary:")
print(f"   Total Roles: {len(open_roles)}")
print(f"   Active Roles: {len(df[df['Status'] == 'Active'])}")
print(f"   Total Open Positions: {df['OpenPositions'].sum()}")
print(f"   Total Target Headcount: {df['TargetHeadcount'].sum()}")
print(f"   Overall Fill Rate: {(df['FilledCount'].sum() / df['TargetHeadcount'].sum() * 100):.1f}%")
print("\n📋 Sample data:")
print(df.head(10).to_string(index=False))


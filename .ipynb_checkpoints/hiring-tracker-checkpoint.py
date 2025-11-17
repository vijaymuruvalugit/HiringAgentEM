import streamlit as st
import pandas as pd

st.title("Hiring Tracker")
st.write("Upload your hiring tracker CSV to see sourcing channel quality summary.")

uploaded_file = st.file_uploader("Choose a CSV file", type="csv")

if uploaded_file is not None:
    df = pd.read_csv(uploaded_file)
    
    # AGGREGATION LOGIC
    rejection_threshold = 60   # %
    resumescore_threshold = 5  # avg score

    result = []
    for source, group in df.groupby('Source'):
        count = len(group)
        rejections = sum(group['Status'].astype(str).str.lower() == 'rejected')
        rejection_rate = rejections / count * 100 if count else 0
        avg_score = group['ResumeScore'].astype(float).mean() if 'ResumeScore' in group else 0
        flagged = "⚠️ Poor Source" if (rejection_rate > rejection_threshold or avg_score < resumescore_threshold) else ""
        result.append({
            'Source': source,
            'Candidates': count,
            'Rejections': rejections,
            'Rejection Rate': f"{rejection_rate:.1f}%",
            'AVG Resume Score': f"{avg_score:.2f}",
            'Flagged': flagged
        })
    
    summary_df = pd.DataFrame(result)
    st.markdown("### Sourcing Effectiveness Summary")
    st.dataframe(summary_df, hide_index=True)

    st.markdown("""
    **Flagged:** ⚠️ Poor Source  
    *Flagged if rejection rate > 60% OR avg resume score < 5.*
    """)
else:
    st.info("Please upload a CSV file to get started.")

import streamlit as st
import pandas as pd
from openai import OpenAI

# Load MALPIP rules
@st.cache_data
def load_rules():
    return pd.read_csv("malpip_rules.csv").to_dict(orient="records")

rules = load_rules()

# Configure OpenAI client
client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

def match_rules(case_text, rules):
    matched = []
    text_lower = case_text.lower()
    for r in rules:
        drug_class = str(r.get("drug_class", "")).lower()
        example_drugs = str(r.get("example_drugs", "")).lower()
        if drug_class in text_lower or any(d.strip() in text_lower for d in example_drugs.split(",")):
            matched.append(r)
    return matched

def query_gpt(case_text, matched_rules):
    context = "\n".join([
        f"{r['drug_class']} – {r['practice_statement_verbatim']}"
        for r in matched_rules
    ])

    prompt = f"""
    You are a clinical assistant using MALPIP criteria.
    Patient case: {case_text}

    Relevant MALPIP rules:
    {context}

    Based on these, explain clearly which medications may be potentially inappropriate and why.
    """

    resp = client.chat.completions.create(
        model="gpt-4o-mini",   # locked to cheapest model
        messages=[{"role": "user", "content": prompt}]
    )
    return resp.choices[0].message.content

# --- Streamlit UI ---
st.title("MALPIP GPT Assistant (Powered by gpt-4o-mini)")

case_text = st.text_area("Enter patient case (free text):")

if st.button("Analyze with GPT"):
    matched = match_rules(case_text, rules)
    if not matched:
        st.info("No specific MALPIP rules matched. GPT will still analyze based on context.")
    explanation = query_gpt(case_text, matched)

    st.subheader("💡 GPT Explanation")
    st.write(explanation)

    if matched:
        st.subheader("📖 Matched MALPIP Rules (verbatim)")
        for r in matched:
            st.markdown(f"""
            **Rule ID:** {r['rule_id']}  
            **Drug class:** {r['drug_class']}  
            **Practice statement:** {r['practice_statement_verbatim']}  
            """)

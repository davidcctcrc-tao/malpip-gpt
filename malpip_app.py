import streamlit as st
import pandas as pd
from openai import OpenAI

# Load MALPIP and DDI rules
@st.cache_data
def load_rules():
    malpip = pd.read_csv("malpip_rules.csv").to_dict(orient="records")
    ddis = pd.read_csv("ddi_rules.csv").to_dict(orient="records")
    return malpip, ddis

malpip_rules, ddi_rules = load_rules()

# Configure OpenAI client
client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

def match_malpip(case_text, rules):
    matched = []
    text_lower = case_text.lower()
    for r in rules:
        drug_class = str(r.get("drug_class", "")).lower()
        example_drugs = str(r.get("example_drugs", "")).lower()
        if drug_class in text_lower or any(d.strip() in text_lower for d in example_drugs.split(",")):
            matched.append(r)
    return matched

def match_ddis(case_text, rules):
    matched = []
    text_lower = case_text.lower()
    for r in rules:
        d1 = str(r["drug1"]).lower()
        d2 = str(r["drug2"]).lower()
        if d1 in text_lower and d2 in text_lower:
            matched.append(r)
    return matched

def query_gpt(case_text, matched_malpip, matched_ddis):
    malpip_context = "\n".join([
        f"MALPIP: {r['drug_class']} – {r['practice_statement_verbatim']}"
        for r in matched_malpip
    ])
    ddi_context = "\n".join([
        f"DDI: {r['drug1']} + {r['drug2']} – {r['interaction_statement_verbatim']} (Severity: {r['severity']})"
        for r in matched_ddis
    ])

    prompt = f"""
    You are a clinical assistant using MALPIP criteria and a list of severe DDIs.
    Patient case: {case_text}

    Relevant MALPIP rules:
    {malpip_context}

    Relevant DDIs:
    {ddi_context}

    Based on these, explain clearly which medications may be potentially inappropriate and why,
    and which combinations may be dangerous.
    """

    resp = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}]
    )
    return resp.choices[0].message.content

# --- Streamlit UI ---
st.title("MALPIP + DDI GPT Assistant (Powered by gpt-4o-mini)")

case_text = st.text_area("Enter patient case (free text):")

if st.button("Analyze with GPT"):
    matched_malpip = match_malpip(case_text, malpip_rules)
    matched_ddis = match_ddis(case_text, ddi_rules)

    if not matched_malpip and not matched_ddis:
        st.info("No specific MALPIP rules or DDIs matched. GPT will still analyze based on context.")

    explanation = query_gpt(case_text, matched_malpip, matched_ddis)

    st.subheader("💡 GPT Explanation")
    st.write(explanation)

    if matched_malpip:
        st.subheader("📖 Matched MALPIP Rules (verbatim)")
        for r in matched_malpip:
            st.markdown(f"""
            **Rule ID:** {r['rule_id']}  
            **Drug class:** {r['drug_class']}  
            **Practice statement:** {r['practice_statement_verbatim']}  
            """)

    if matched_ddis:
        st.subheader("⚠️ Matched DDI Rules (verbatim)")
        for r in matched_ddis:
            st.markdown(f"""
            **DDI ID:** {r['ddi_id']}  
            **Drugs:** {r['drug1']} + {r['drug2']}  
            **Interaction:** {r['interaction_statement_verbatim']}  
            **Severity:** {r['severity']}  
            **Recommendation:** {r['recommendation']}  
            """)

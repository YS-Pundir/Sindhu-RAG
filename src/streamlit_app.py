import streamlit as st

# --- Streamlit UI ---
st.title("ABB Manuals RAG Assistant")
st.markdown("Ask questions about the ABB ACS880 drive manual.")

user_query = st.text_input("Enter your question here:", "My ACS880 drive just tripped with fault code 2310. What does this mean and what should I check?")

if st.button("Get Answer"):
    if user_query:
        with st.spinner("Finding the answer..."):
            answer = rag_qa(user_query)
            st.write("**Answer:**")
            st.write(answer)
    else:
        st.warning("Please enter a question.")

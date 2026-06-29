

import streamlit as st
from rag_pipelines import generate_answer,retrieve_chunks,retriever,build_user_message,loading_prompt,bundle
SYSTEM_MESSAGE = loading_prompt(bundle).strip()


# 1. Setup the UI title
st.title("Ancient Chatbot")

# 2. Initialize chat history in session state if it doesn't exist
if "messages" not in st.session_state:
    st.session_state.messages = []

# 3. Display chat messages from history on app rerun
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# 4. Accept user input
if prompt := st.chat_input("Ask about the Indus Valley Civilisation report"):
    # Display user message
    with st.chat_message("user"):
        st.markdown(prompt)
    st.session_state.messages.append({"role": "user", "content": prompt})
    context =retrieve_chunks(prompt,retriever)
    user_message_content = build_user_message(prompt, context)

    # 5. Generate response using your existing RAG logic
    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            # Ensure your rag_answer function returns a dict with "answer"
            result = generate_answer(user_message_content,SYSTEM_MESSAGE)
            response = result
            st.markdown(response)
    
    # Add assistant response to history
    st.session_state.messages.append({"role": "assistant", "content": response})

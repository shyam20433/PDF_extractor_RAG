import sys
import rag_engine  # Import module instead of variables
import time

def main():
    print("Initializing RAG Engine...")
    
    # Load the FAISS index and metadata
    if not rag_engine.load_objects():
        print("❌ Error: Could not load index. Make sure you have processed a PDF first.")
        print("Run 'python app.py' and upload a PDF via the web interface.")
        return

    print(f"✅ Loaded {len(rag_engine.chunks)} text chunks.")
    print("\n" + "="*50)
    print("  🤖 CLI RAG Query Tool")
    print("  Type 'exit' or 'quit' to stop")
    print("="*50 + "\n")

    while True:
        try:
            question = input("\n👉 Ask a question: ").strip()
            
            if not question:
                continue
                
            if question.lower() in ['exit', 'quit']:
                print("Goodbye! 👋")
                break

            print("⏳ Thinking...", end="\r", flush=True)
            
            try:
                # Get answer (pass None for socketio since we're in CLI)
                answer, sources = rag_engine.answer_question(question, socketio=None)
                
                # Clear thinking line
                print(" " * 20, end="\r")
                
                print(f"\n📝 \033[1mAnswer:\033[0m")
                print(f"\033[96m{answer}\033[0m") # Cyan text
                
                print(f"\n📚 \033[1mSources:\033[0m")
                for i, source in enumerate(sources, 1):
                    # Clean up source text for display
                    text = source['text'].replace('\n', ' ').strip()
                    print(f"  {i}. [Page {source['page']}] {text}")
                    
            except Exception as e:
                print(f"\n❌ Error: {str(e)}")

        except KeyboardInterrupt:
            print("\nGoodbye! 👋")
            break

if __name__ == "__main__":
    main()

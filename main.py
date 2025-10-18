"""
MathVizAI - Automated Mathematical Video Generation
A system that solves math problems, validates solutions, and generates
synchronized educational videos with visualizations and audio narration.

Author: anirudhsengar
Repository: https://github.com/anirudhsengar/MathVizAI
"""

from pipeline.orchestrator import PipelineOrchestrator
import sys


def main():
    """Main entry point for MathVizAI"""
    
    print("""
    ███╗   ███╗ █████╗ ████████╗██╗  ██╗██╗   ██╗██╗███████╗ █████╗ ██╗
    ████╗ ████║██╔══██╗╚══██╔══╝██║  ██║██║   ██║██║╚══███╔╝██╔══██╗██║
    ██╔████╔██║███████║   ██║   ███████║██║   ██║██║  ███╔╝ ███████║██║
    ██║╚██╔╝██║██╔══██║   ██║   ██╔══██║╚██╗ ██╔╝██║ ███╔╝  ██╔══██║██║
    ██║ ╚═╝ ██║██║  ██║   ██║   ██║  ██║ ╚████╔╝ ██║███████╗██║  ██║██║
    ╚═╝     ╚═╝╚═╝  ╚═╝   ╚═╝   ╚═╝  ╚═╝  ╚═══╝  ╚═╝╚══════╝╚═╝  ╚═╝╚═╝
    
    Automated Mathematical Video Generation System
    """)
    
    try:
        # Initialize the pipeline
        orchestrator = PipelineOrchestrator()
        
        # Interactive mode
        print("Enter mathematical problems to solve and visualize.")
        print("Type 'exit', 'quit', or 'q' to stop.\n")
        
        while True:
            try:
                query = input("\n🔢 Enter math problem: ").strip()
                
                if not query:
                    print("Please enter a problem.")
                    continue
                
                if query.lower() in ["exit", "quit", "q"]:
                    print("\n👋 Goodbye! Thanks for using MathVizAI.")
                    break
                
                # Process the query through the complete pipeline
                result = orchestrator.process_query(query)
                
                print(f"\n✅ All files saved to: {result['session_folder']}")
                
            except KeyboardInterrupt:
                print("\n\n⚠ Interrupted by user")
                break
            except Exception as e:
                print(f"\n❌ Error processing query: {str(e)}")
                import traceback
                traceback.print_exc()
                print("\nYou can try again with a different problem.\n")
    
    except Exception as e:
        print(f"\n❌ Fatal error: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()


# Project Goals (Implementation Roadmap)
# =====================================
# ✅ 1. LLM answers the question along with the proof
# ✅ 2. 2nd iteration to make sure the LLM is right and hasn't made any mistakes (Judge LLM)
# ✅ 3. Generate audio script explaining the answer
# ✅ 4. Generate python script according to the audio script
# 🔄 5. Split audio script into manageable portions for the TTS model to generate the audio (PARTIAL - segments created, TTS integration pending)
# ⏳ 6. Run the python script and get the videos (Manual step - see rendering_instructions.txt)
# ⏳ 7. Align the audio and video together (TO BE IMPLEMENTED)
# ⏳ 8. Save the video (TO BE IMPLEMENTED)

# Goal
# 1. LLM answers the question along with the proof
# 2. 2nd iteration to make sure the LLM is right and hasn't made any mistakes (Judge LLM)
# 3. Generate audio script explaining the answer
# 4. Generate python script according to the audio script
# 5. Split audio script into managable portions for the TTS model to generate the audio
# 6. Run the python script and get the videos
# 7. Align the audio and video together
# 8. Save the video
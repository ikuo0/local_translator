import argparse
import json
import sys

from .ollama import OllamaClient


def main() -> int:
    parser = argparse.ArgumentParser(description="Ollama API client")
    parser.add_argument("--host", default="http://localhost:11434", help="Ollama server URL")
    parser.add_argument("--model", default="qwen3:8b", help="Model name")
    
    subparsers = parser.add_subparsers(dest="command", help="Command to execute")
    
    # Generate command
    gen_parser = subparsers.add_parser("generate", help="Generate text")
    gen_parser.add_argument("--prompt", required=True, help="Input prompt")
    gen_parser.add_argument("--system", help="System prompt")
    gen_parser.add_argument("--temperature", type=float, default=0.7, help="Temperature (default: 0.7)")
    gen_parser.add_argument("--keep-alive", default="5m", help="Keep model alive time (default: 5m)")
    
    # Chat command
    chat_parser = subparsers.add_parser("chat", help="Chat with model")
    chat_parser.add_argument("--message", required=True, help="User message")
    chat_parser.add_argument("--system", help="System prompt")
    chat_parser.add_argument("--temperature", type=float, default=0.7, help="Temperature (default: 0.7)")
    chat_parser.add_argument("--keep-alive", default="5m", help="Keep model alive time (default: 5m)")
    
    # List models command
    subparsers.add_parser("list-models", help="List available models")
    
    # Model info command
    info_parser = subparsers.add_parser("model-info", help="Get model information")
    
    # Unload command
    subparsers.add_parser("unload", help="Unload model from memory")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 1
    
    client = OllamaClient(host=args.host, model=args.model)
    
    try:
        if args.command == "generate":
            response = client.generate(
                prompt=args.prompt,
                system=args.system,
                temperature=args.temperature,
                keep_alive=args.keep_alive,
            )
            print(response)
            
        elif args.command == "chat":
            response = client.chat(
                messages=[{"role": "user", "content": args.message}],
                system=args.system,
                temperature=args.temperature,
                keep_alive=args.keep_alive,
            )
            print(response)
            
        elif args.command == "list-models":
            models = client.list_models()
            print(json.dumps(models, indent=2))
            
        elif args.command == "model-info":
            info = client.get_model_info()
            print(json.dumps(info, indent=2))
            
        elif args.command == "unload":
            client.unload_model()
            print("Model unloaded")
        
        return 0
        
    except Exception as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

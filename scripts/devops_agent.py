import os
import sys
import argparse
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough
from langchain_core.runnables.branch import RunnableBranch

# ==========================================
# 1. Prompts for Language Detection & Specialists
# ==========================================

DETECT_LANGUAGE_PROMPT = PromptTemplate.from_template(
    """Analyze the following CI/CD build or execution log and identify the primary programming language, framework, or tool that caused the failure.
    Return ONLY the name of the language/technology in a single word (e.g., DOTNET, PYTHON, TYPESCRIPT, JAVASCRIPT, JAVA, GO, RUST, DOCKER, TERRAFORM, UNKNOWN).
    
    Log Error snippet:
    {log_content}
    
    Detected Language:"""
)

# Specialist prompts
DOTNET_EXPERT_PROMPT = PromptTemplate.from_template(
    """Você é um Engenheiro DevOps Sênior especialista em C# e .NET. 
    Analise o log de erro de build abaixo e:
    1. Explique a causa raiz do problema de forma clara.
    2. Sugira a correção exata no código ou no comando do CLI do .NET.
    3. Retorne a resposta formatada em Markdown, usando blocos de código onde apropriado.
    
    Log do erro:
    {log_content}
    
    Análise do Especialista .NET:"""
)

PYTHON_EXPERT_PROMPT = PromptTemplate.from_template(
    """Você é um Engenheiro DevOps Sênior especialista em Python (pip, poetry, pytest, scripts, etc). 
    Analise o log de erro de build/execução abaixo e:
    1. Explique a causa raiz do problema de forma detalhada.
    2. Liste os passos ou comandos corrigidos para resolver a falha.
    3. Retorne a resposta formatada em Markdown, usando blocos de código onde apropriado.
    
    Log do erro:
    {log_content}
    
    Análise do Especialista Python:"""
)

TYPESCRIPT_EXPERT_PROMPT = PromptTemplate.from_template(
    """Você é um Engenheiro DevOps Sênior especialista em TypeScript/JavaScript (Node.js, npm, yarn, tsc, frameworks frontend/backend). 
    Analise o log do erro de build ou teste abaixo e:
    1. Identifique o arquivo e a linha onde o erro ocorreu (se aplicável), e explique o motivo.
    2. Sugira o ajuste no código, configuração (tsconfig.json, package.json) ou dependências para corrigir o problema.
    3. Retorne a resposta formatada em Markdown, com exemplos de código.
    
    Log do erro:
    {log_content}
    
    Análise do Especialista TypeScript/JS:"""
)

GENERAL_EXPERT_PROMPT = PromptTemplate.from_template(
    """Você é um Especialista de Infraestrutura e DevOps (Linux, Shell, Docker, GitHub Actions, Genérico).
    Analise este log de falha de job do CI/CD e:
    1. Explique de forma concisa por que o job falhou.
    2. Forneça a solução proposta.
    3. Retorne em Markdown.
    
    Log do erro:
    {log_content}
    
    Análise Geral DevOps:"""
)

# ==========================================
# 2. Routing Logic
# ==========================================

def _route_by_language(info):
    lang = info["language"].strip().upper()
    print(f"[*] Detected technology context: {lang}")
    
    if "DOTNET" in lang or "C#" in lang or "CSHARP" in lang:
        return DOTNET_EXPERT_PROMPT
    elif "PYTHON" in lang:
        return PYTHON_EXPERT_PROMPT
    elif "TYPESCRIPT" in lang or "JAVASCRIPT" in lang or "NODE" in lang:
        return TYPESCRIPT_EXPERT_PROMPT
    else:
        return GENERAL_EXPERT_PROMPT

# ==========================================
# 3. Main Agent Execution Function
# ==========================================

def analyze_error(log_content: str):
    """Orchestrates the LLM calls to analyze the build error using LangChain."""
    
    # Needs GEMINI_API_KEY environment variable set
    if "GEMINI_API_KEY" not in os.environ and "GOOGLE_API_KEY" not in os.environ:
        print("Error: GEMINI_API_KEY or GOOGLE_API_KEY environment variable not found.")
        sys.exit(1)
        
    llm = ChatGoogleGenerativeAI(
        model="gemini-2.5-pro", # You can use gemini-2.0-flash if 2.5 is not accessible, but 2.5-pro is generally best for coding
        temperature=0.1,
        max_output_tokens=2048
    )

    # Chain to detect language
    detection_chain = (
        DETECT_LANGUAGE_PROMPT 
        | llm 
        | StrOutputParser()
    )

    # Route to the specialist prompt based on detected language, then call LLM
    specialist_chain = (
        {"log_content": lambda x: x["log_content"], "language": detection_chain}
        | RunnablePassthrough.assign(prompt=_route_by_language)
        | (lambda x: x["prompt"].format(log_content=x["log_content"]))
        | llm
        | StrOutputParser()
    )

    print("[*] Starting AI Analysis of the logs...")
    try:
        result = specialist_chain.invoke({"log_content": log_content})
        return result
    except Exception as e:
        print(f"Error during AI analysis: {e}")
        return f"### Erro na Análise da IA\nNão foi possível analisar o erro. Detalhes: `{e}`"

# ==========================================
# 4. CLI Entrypoint & GitHub Summary Logic
# ==========================================

def append_to_github_summary(markdown_content: str):
    """Appends the markdown content to the GitHub Actions Job Summary if available."""
    summary_file = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary_file and os.path.exists(summary_file):
        with open(summary_file, "a", encoding="utf-8") as f:
            f.write("\n\n" + markdown_content + "\n")
        print(f"[*] Analysis successfully written to GitHub Step Summary.")
    else:
        print("[*] GITHUB_STEP_SUMMARY environment variable not found or file does not exist. Outputting to console only.")

def main():
    parser = argparse.ArgumentParser(description="DevOps AI Agent to analyze CI/CD build errors.")
    parser.add_argument("--log-file", type=str, required=True, help="Path to the file containing the failed job logs.")
    
    args = parser.parse_args()
    
    log_path = args.log_file
    if not os.path.exists(log_path):
        print(f"Error: Log file '{log_path}' not found.")
        sys.exit(1)
        
    with open(log_path, "r", encoding="utf-8", errors="ignore") as f:
        # We might want to limit the log size to avoid hitting LLM context limits.
        # Grabbing the last 15000 characters is usually a good heuristic for build errors.
        full_log = f.read()
        log_snippet = full_log[-15000:] if len(full_log) > 15000 else full_log
        
    if not log_snippet.strip():
        print("Log file is empty.")
        sys.exit(0)

    # Run analysis
    analysis_markdown = analyze_error(log_snippet)
    
    # Format a nice header
    final_output = f"## 🤖 DevOps AI-Reviewer - Análise de Falha\n\n{analysis_markdown}"
    
    print("\n" + "="*50)
    print(final_output)
    print("="*50 + "\n")
    
    # Write to Summary
    append_to_github_summary(final_output)

if __name__ == "__main__":
    # Workaround for Google API Key if they set GEMINI_API_KEY
    if "GEMINI_API_KEY" in os.environ and "GOOGLE_API_KEY" not in os.environ:
        os.environ["GOOGLE_API_KEY"] = os.environ["GEMINI_API_KEY"]
        
    main()

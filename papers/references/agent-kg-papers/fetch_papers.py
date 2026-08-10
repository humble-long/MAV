#!/usr/bin/env python3
"""
下载 Agent+KG 相关论文到本文件夹，并推送元数据到 Zotero 本地 connector。
"""
import os, time, uuid, json, subprocess, urllib.request, urllib.error

PAPERS = [
    # ─── Category A: Agent 框架 ───────────────────────────────────
    {
        "arxiv": "2210.03629",
        "title": "ReAct: Synergizing Reasoning and Acting in Language Models",
        "creators": [
            {"firstName": "Shunyu", "lastName": "Yao", "creatorType": "author"},
            {"firstName": "Jeffrey", "lastName": "Zhao", "creatorType": "author"},
            {"firstName": "Dian", "lastName": "Yu", "creatorType": "author"},
            {"firstName": "Nan", "lastName": "Du", "creatorType": "author"},
            {"firstName": "Izhak", "lastName": "Shafran", "creatorType": "author"},
            {"firstName": "Karthik", "lastName": "Narasimhan", "creatorType": "author"},
            {"firstName": "Yuan", "lastName": "Cao", "creatorType": "author"},
        ],
        "date": "2023",
        "venue": "ICLR 2023",
        "tag": "A-agent",
        "abstract": "Explores synergizing reasoning traces and task-specific actions in LLMs. The agent interleaves Thought-Action-Observation to solve tasks with verifiable external interactions.",
    },
    {
        "arxiv": "2307.07697",
        "title": "Think-on-Graph: Deep and Responsible Reasoning of Large Language Model on Knowledge Graph",
        "creators": [
            {"firstName": "Jiashuo", "lastName": "Sun", "creatorType": "author"},
            {"firstName": "Chengjin", "lastName": "Xu", "creatorType": "author"},
            {"firstName": "Lumingyuan", "lastName": "Tang", "creatorType": "author"},
            {"firstName": "Saizhuo", "lastName": "Wang", "creatorType": "author"},
            {"firstName": "Chen", "lastName": "Lin", "creatorType": "author"},
            {"firstName": "Yeyun", "lastName": "Gong", "creatorType": "author"},
            {"firstName": "Heung-Yeung", "lastName": "Shum", "creatorType": "author"},
            {"firstName": "Jian", "lastName": "Guo", "creatorType": "author"},
        ],
        "date": "2024",
        "venue": "ICLR 2024",
        "tag": "A-agent",
        "abstract": "LLM as agent doing beam search on KG, iteratively exploring reasoning paths. Training-free, achieves SOTA on 6/9 KGQA datasets.",
    },
    {
        "arxiv": "2410.23875",
        "title": "Plan-on-Graph: Self-Correcting Adaptive Planning of Large Language Model on Knowledge Graphs",
        "creators": [
            {"firstName": "Liyi", "lastName": "Chen", "creatorType": "author"},
            {"firstName": "Panrong", "lastName": "Tong", "creatorType": "author"},
            {"firstName": "Zhongming", "lastName": "Jin", "creatorType": "author"},
            {"firstName": "Ying", "lastName": "Sun", "creatorType": "author"},
            {"firstName": "Jieping", "lastName": "Ye", "creatorType": "author"},
            {"firstName": "Hui", "lastName": "Xiong", "creatorType": "author"},
        ],
        "date": "2024",
        "venue": "NeurIPS 2024",
        "tag": "A-agent",
        "abstract": "Self-correcting adaptive planning on KGs: decomposes question into sub-objectives, uses Guidance/Memory/Reflection to explore and correct reasoning paths.",
    },
    {
        "arxiv": "2502.03283",
        "title": "SymAgent: A Neural-Symbolic Self-Learning Agent Framework for Complex Reasoning over Knowledge Graphs",
        "creators": [
            {"firstName": "Ben", "lastName": "Liu", "creatorType": "author"},
            {"firstName": "Jihai", "lastName": "Zhang", "creatorType": "author"},
            {"firstName": "Fangquan", "lastName": "Lin", "creatorType": "author"},
            {"firstName": "Cheng", "lastName": "Yang", "creatorType": "author"},
            {"firstName": "Min", "lastName": "Peng", "creatorType": "author"},
            {"firstName": "Wai", "lastName": "Yin", "creatorType": "author"},
        ],
        "date": "2025",
        "venue": "WWW 2025",
        "tag": "A-agent",
        "abstract": "Neural-symbolic agent: Agent-Planner extracts symbolic rules for question decomposition; Agent-Executor invokes tools combining KG and external docs. Self-learning via online exploration + offline policy update.",
    },
    {
        "arxiv": "2410.11531",
        "title": "AGENTiGraph: An Interactive Knowledge Graph Platform for LLM-based Chatbots Utilizing Private Data",
        "creators": [
            {"firstName": "Xinjie", "lastName": "Zhao", "creatorType": "author"},
            {"firstName": "Moritz", "lastName": "Blum", "creatorType": "author"},
            {"firstName": "Rui", "lastName": "Yang", "creatorType": "author"},
        ],
        "date": "2024",
        "venue": "arXiv 2024",
        "tag": "A-agent",
        "abstract": "Multi-agent platform for KG-based chatbots: User Intent Agent + Dynamic Knowledge Integration Agent. 95.12% task classification accuracy, 90.45% task execution success.",
    },
    # ─── Category B: GraphRAG / KG+LLM ──────────────────────────
    {
        "arxiv": "2404.16130",
        "title": "From Local to Global: A Graph RAG Approach to Query-Focused Summarization",
        "creators": [
            {"firstName": "Darren", "lastName": "Edge", "creatorType": "author"},
            {"firstName": "Ha", "lastName": "Trinh", "creatorType": "author"},
            {"firstName": "Newman", "lastName": "Cheng", "creatorType": "author"},
            {"firstName": "Joshua", "lastName": "Bradley", "creatorType": "author"},
        ],
        "date": "2024",
        "venue": "arXiv 2024 (Microsoft Research)",
        "tag": "B-graphrag",
        "abstract": "Microsoft GraphRAG: community detection + hierarchical summaries for global query-focused summarization over large document corpora.",
    },
    {
        "arxiv": "2409.13731",
        "title": "KAG: Boosting LLMs in Professional Domains via Knowledge Augmented Generation",
        "creators": [
            {"firstName": "Lei", "lastName": "Liang", "creatorType": "author"},
            {"firstName": "Mengshu", "lastName": "Sun", "creatorType": "author"},
            {"firstName": "Zhengke", "lastName": "Gui", "creatorType": "author"},
        ],
        "date": "2025",
        "venue": "WWW 2025",
        "tag": "B-graphrag",
        "abstract": "Professional domain KG+LLM framework. LLM-friendly knowledge representation, mutual-indexing KG+text chunks, logical-form-guided reasoning. +19.6% on 2Wiki, +33.5% on HotpotQA vs RAG.",
    },
    {
        "arxiv": "2408.08921",
        "title": "Graph Retrieval-Augmented Generation: A Survey",
        "creators": [
            {"firstName": "Boci", "lastName": "Peng", "creatorType": "author"},
            {"firstName": "Yun", "lastName": "Zhu", "creatorType": "author"},
            {"firstName": "Yongchao", "lastName": "Liu", "creatorType": "author"},
        ],
        "date": "2025",
        "venue": "ACM Transactions on Information Systems 2025",
        "tag": "B-graphrag",
        "abstract": "Comprehensive survey of GraphRAG: query, retrieval, generation. Taxonomy of graph types, indexing strategies, and application domains.",
    },
    {
        "arxiv": "2306.08302",
        "title": "Unifying Large Language Models and Knowledge Graphs: A Roadmap",
        "creators": [
            {"firstName": "Shirui", "lastName": "Pan", "creatorType": "author"},
            {"firstName": "Linhao", "lastName": "Luo", "creatorType": "author"},
            {"firstName": "Yufei", "lastName": "Wang", "creatorType": "author"},
            {"firstName": "Chen", "lastName": "Chen", "creatorType": "author"},
            {"firstName": "Jiapu", "lastName": "Wang", "creatorType": "author"},
            {"firstName": "Xindong", "lastName": "Wu", "creatorType": "author"},
        ],
        "date": "2024",
        "venue": "IEEE Transactions on Knowledge and Data Engineering 2024",
        "tag": "B-graphrag",
        "abstract": "Roadmap for unifying LLMs and KGs: KG-enhanced LLMs, LLM-augmented KGs, synergized LLM+KG approaches for reasoning and question answering.",
    },
    {
        "arxiv": "2501.13958",
        "title": "A Survey of Graph Retrieval-Augmented Generation for Customized Large Language Models",
        "creators": [
            {"firstName": "Xuanyi", "lastName": "Li", "creatorType": "author"},
            {"firstName": "Rui", "lastName": "Zhao", "creatorType": "author"},
            {"firstName": "Yuequn", "lastName": "Cheng", "creatorType": "author"},
        ],
        "date": "2025",
        "venue": "arXiv 2025",
        "tag": "B-graphrag",
        "abstract": "Survey of GraphRAG for customized LLMs: graph construction, retrieval, generation, evaluation. Covers domain-specific applications.",
    },
    # ─── Category C: RAG / Tool use ─────────────────────────────
    {
        "arxiv": "2005.11401",
        "title": "Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks",
        "creators": [
            {"firstName": "Patrick", "lastName": "Lewis", "creatorType": "author"},
            {"firstName": "Ethan", "lastName": "Perez", "creatorType": "author"},
            {"firstName": "Aleksandra", "lastName": "Piktus", "creatorType": "author"},
        ],
        "date": "2020",
        "venue": "NeurIPS 2020",
        "tag": "C-rag",
        "abstract": "Original RAG paper: retrieval-augmented generation combining parametric and non-parametric memory for open-domain QA.",
    },
    {
        "arxiv": "2307.16789",
        "title": "ToolLLM: Facilitating Large Language Models to Master 16000+ Real-world APIs",
        "creators": [
            {"firstName": "Yujia", "lastName": "Qin", "creatorType": "author"},
            {"firstName": "Shihao", "lastName": "Liang", "creatorType": "author"},
            {"firstName": "Yining", "lastName": "Ye", "creatorType": "author"},
        ],
        "date": "2024",
        "venue": "ICLR 2024",
        "tag": "C-rag",
        "abstract": "ToolLLM: training LLMs to use real-world APIs via instruction tuning on ToolBench. Demonstrates tool-augmented LLM generalization.",
    },
]


def download_pdf(arxiv_id: str, save_dir: str) -> str:
    url = f"https://arxiv.org/pdf/{arxiv_id}"
    fname = os.path.join(save_dir, f"{arxiv_id}.pdf")
    if os.path.exists(fname):
        print(f"  [skip] {arxiv_id}.pdf already exists")
        return fname
    print(f"  [down] {arxiv_id} ...", end=" ", flush=True)
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=30) as r, open(fname, "wb") as f:
            f.write(r.read())
        print("OK")
        return fname
    except Exception as e:
        print(f"FAIL ({e})")
        return ""


def push_to_zotero(paper: dict) -> bool:
    arxiv_id = paper["arxiv"]
    item = {
        "itemType": "preprint",
        "title": paper["title"],
        "creators": paper["creators"],
        "date": paper["date"],
        "repository": "arXiv",
        "archiveID": f"arXiv:{arxiv_id}",
        "url": f"https://arxiv.org/abs/{arxiv_id}",
        "abstractNote": paper.get("abstract", ""),
        "extra": f"venue: {paper.get('venue','')}\ntag: {paper.get('tag','')}",
    }
    payload = json.dumps({
        "sessionID": str(uuid.uuid4()),
        "items": [item],
        "attachments": [],
    }).encode()

    import urllib.request
    req = urllib.request.Request(
        "http://127.0.0.1:23119/connector/saveItems",
        data=payload,
        headers={
            "Content-Type": "application/json",
            "X-Zotero-Connector-Version": "4.0.29",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            ok = r.status in (200, 201)
            print(f"  [zotero] {arxiv_id} -> HTTP {r.status}")
            return ok
    except Exception as e:
        print(f"  [zotero] {arxiv_id} FAIL ({e})")
        return False


def main():
    save_dir = os.path.dirname(os.path.abspath(__file__))
    print(f"Save dir: {save_dir}\n")

    for i, paper in enumerate(PAPERS, 1):
        arxiv_id = paper["arxiv"]
        print(f"[{i:02d}/{len(PAPERS)}] {paper['title'][:60]}...")
        download_pdf(arxiv_id, save_dir)
        time.sleep(1)  # be polite to arXiv
        push_to_zotero(paper)
        time.sleep(0.5)
        print()

    print("Done. Check Zotero 'My Library' for new preprint items.")
    print("Recommended: create a 'Agent+KG Papers' collection in Zotero and move them there.")


if __name__ == "__main__":
    main()

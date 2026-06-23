"""
GraphRAG and Skill Ontology Engine.
Constructs a property graph (using SQLite persistence) representing skills, candidates, jobs,
and certifications. Combines vector search with graph traversal (neighborhood expansion).
"""

import json
import logging
import sqlite3
from typing import Dict, List, Any
from core.db import DB_PATH

logger = logging.getLogger(__name__)

class GraphRAG:
    """
    GraphRAG engine managing nodes/edges for career ontology and candidate intelligence retrieval.
    """

    @staticmethod
    def init_graph_db():
        """Creates the graph tables if they don't exist."""
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            
            # Nodes Table
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS graph_nodes (
                id TEXT PRIMARY KEY,
                label TEXT,
                type TEXT, -- skill, candidate, job, company, certification, project
                properties TEXT
            )
            """)

            # Edges Table
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS graph_edges (
                source TEXT,
                target TEXT,
                type TEXT, -- HAS_SKILL, RELATES_TO, WORKED_AT, REQUIRED_FOR, CERTIFIED_IN
                weight REAL DEFAULT 1.0,
                PRIMARY KEY (source, target, type),
                FOREIGN KEY (source) REFERENCES graph_nodes(id) ON DELETE CASCADE,
                FOREIGN KEY (target) REFERENCES graph_nodes(id) ON DELETE CASCADE
            )
            """)
            
            conn.commit()
            conn.close()
            logger.info("GraphRAG database schemas initialized.")
            
            # Populate ontology seed data
            GraphRAG._seed_ontology()
        except Exception as e:
            logger.error(f"Failed to initialize graph tables: {e}")

    @staticmethod
    def _seed_ontology():
        """Pre-populates basic skill graph ontology structure."""
        # Nodes
        skills = [
            ("python", "Python", "skill"),
            ("fastapi", "FastAPI", "skill"),
            ("api_backend", "API Backend", "skill"),
            ("pytorch", "PyTorch", "skill"),
            ("mlops", "MLOps", "skill"),
            ("langgraph", "LangGraph", "skill"),
            ("agent_orchestration", "Agent Orchestration", "skill"),
            ("chromadb", "ChromaDB", "skill"),
            ("pgvector", "pgvector", "skill"),
            ("qdrant", "Qdrant", "skill"),
            ("retrieval_memory", "Retrieval Memory", "skill"),
            ("docker", "Docker", "skill"),
            ("kubernetes", "Kubernetes", "skill"),
            ("cicd", "CI-CD", "skill"),
            ("deployment_maturity", "Deployment Maturity", "skill"),
        ]
        
        # Edges
        relations = [
            ("fastapi", "python", "RELATES_TO", 1.0),
            ("fastapi", "api_backend", "RELATES_TO", 0.9),
            ("pytorch", "python", "RELATES_TO", 1.0),
            ("pytorch", "mlops", "RELATES_TO", 0.8),
            ("langgraph", "agent_orchestration", "RELATES_TO", 1.0),
            ("langgraph", "python", "RELATES_TO", 0.9),
            ("chromadb", "retrieval_memory", "RELATES_TO", 1.0),
            ("pgvector", "retrieval_memory", "RELATES_TO", 1.0),
            ("qdrant", "retrieval_memory", "RELATES_TO", 1.0),
            ("docker", "deployment_maturity", "RELATES_TO", 0.9),
            ("kubernetes", "deployment_maturity", "RELATES_TO", 1.0),
            ("cicd", "deployment_maturity", "RELATES_TO", 0.9),
        ]

        for nid, lbl, typ in skills:
            GraphRAG.upsert_node(nid, lbl, typ, {})
            
        for src, tgt, typ, w in relations:
            GraphRAG.upsert_edge(src, tgt, typ, w)

    @staticmethod
    def upsert_node(node_id: str, label: str, node_type: str, properties: Dict[str, Any]):
        """Inserts or updates a node in the graph."""
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute(
                "INSERT OR REPLACE INTO graph_nodes (id, label, type, properties) VALUES (?, ?, ?, ?)",
                (node_id.lower().strip(), label, node_type, json.dumps(properties))
            )
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"Error upserting graph node {node_id}: {e}")

    @staticmethod
    def upsert_edge(source: str, target: str, edge_type: str, weight: float = 1.0):
        """Inserts or updates a directed, weighted relationship between nodes."""
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute(
                "INSERT OR REPLACE INTO graph_edges (source, target, type, weight) VALUES (?, ?, ?, ?)",
                (source.lower().strip(), target.lower().strip(), edge_type.upper().strip(), weight)
            )
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"Error upserting graph edge {source} -> {target}: {e}")

    @staticmethod
    def get_adjacent_skills(skill: str, max_hops: int = 1) -> List[Dict[str, Any]]:
        """Retrieves related/adjacent skills through graph neighborhood expansion."""
        GraphRAG.init_graph_db()
        results = []
        visited = set()
        
        # Normalize skill input
        start_skill = skill.lower().strip()
        queue = [(start_skill, 0, 1.0)] # node_id, current_hops, combined_weight
        visited.add(start_skill)

        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()

            while queue:
                current_node, hops, path_weight = queue.pop(0)
                if hops >= max_hops:
                    continue

                # Search outward edges (source to target)
                cursor.execute(
                    "SELECT target, type, weight FROM graph_edges WHERE source = ?",
                    (current_node,)
                )
                for tgt, etype, w in cursor.fetchall():
                    if tgt not in visited:
                        visited.add(tgt)
                        results.append({
                            "skill_id": tgt,
                            "hops": hops + 1,
                            "type": etype,
                            "relevance": path_weight * w
                        })
                        queue.append((tgt, hops + 1, path_weight * w))

                # Search inward edges (target to source)
                cursor.execute(
                    "SELECT source, type, weight FROM graph_edges WHERE target = ?",
                    (current_node,)
                )
                for src, etype, w in cursor.fetchall():
                    if src not in visited:
                        visited.add(src)
                        results.append({
                            "skill_id": src,
                            "hops": hops + 1,
                            "type": etype,
                            "relevance": path_weight * w
                        })
                        queue.append((src, hops + 1, path_weight * w))

            conn.close()
        except Exception as e:
            logger.error(f"Failed traversing graph: {e}")
            
        return sorted(results, key=lambda x: x["relevance"], reverse=True)

    @staticmethod
    def query_graph_rag(query: str) -> Dict[str, Any]:
        """
        Combines vector semantic concepts with graph ontology path matching.
        """
        GraphRAG.init_graph_db()
        # Find key tokens in query matching seed graph nodes
        tokens = query.lower().split()
        matched_nodes = []
        suggested_neighborhoods = []

        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            
            # Simple keyword matching to find query seeds in the graph database
            for token in tokens:
                cursor.execute(
                    "SELECT id, label, type, properties FROM graph_nodes WHERE id LIKE ?",
                    (f"%{token}%",)
                )
                for row in cursor.fetchall():
                    node_id, label, ntype, props = row
                    matched_nodes.append({
                        "id": node_id,
                        "label": label,
                        "type": ntype,
                        "properties": json.loads(props or "{}")
                    })
                    
                    # Walk neighbors for each match
                    neighbors = GraphRAG.get_adjacent_skills(node_id, max_hops=2)
                    for n in neighbors:
                        suggested_neighborhoods.append(n)

            conn.close()
        except Exception as e:
            logger.error(f"Error querying GraphRAG: {e}")

        # Deduplicate recommendations
        deduped_suggestions = {}
        for item in suggested_neighborhoods:
            s_id = item["skill_id"]
            if s_id not in deduped_suggestions or item["relevance"] > deduped_suggestions[s_id]["relevance"]:
                deduped_suggestions[s_id] = item

        return {
            "query": query,
            "matched_entities": matched_nodes,
            "ontology_recommendations": list(deduped_suggestions.values())[:8]
        }

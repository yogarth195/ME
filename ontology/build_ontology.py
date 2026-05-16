"""Build skill_ontology.gpickle from hardcoded edge definitions."""

import json
import pickle
from pathlib import Path

import networkx as nx

ONTOLOGY_DIR = Path(__file__).parent


def build_graph() -> nx.DiGraph:
    G = nx.DiGraph()

    # ── Skill nodes (no domain labels — skills are cross-domain by nature) ─────
    # Domain detection is handled at inference time via A+B approach (role profiles + SBERT)
    skill_nodes = [
        # AI / ML / DS
        "artificial_intelligence", "machine_learning", "deep_learning",
        "natural_language_processing", "computer_vision", "reinforcement_learning",
        "generative_ai", "large_language_models", "retrieval_augmented_generation",
        "generative_adversarial_networks", "tensorflow", "pytorch", "scikit_learn",
        "xgboost", "lightgbm", "huggingface", "keras", "numpy", "pandas",
        "matplotlib", "seaborn", "opencv", "nltk", "spacy", "bert",
        "transformers_lib", "stable_diffusion", "langchain", "llamaindex",
        # Web
        "html", "css", "sass", "react", "vue", "angular", "svelte",
        "nextjs", "nuxtjs", "express", "fastapi", "flask", "django", "rails",
        "graphql", "rest", "websockets", "tailwindcss", "bootstrap",
        "webpack", "vite", "jest", "cypress", "redux", "prisma",
        "authentication", "deployment",
        # DevOps
        "docker", "kubernetes", "cicd", "github_actions", "gitlab_cicd",
        "jenkins", "terraform", "ansible", "helm", "prometheus",
        "grafana", "nginx", "iac",
        # Cloud
        "amazon_web_services", "google_cloud", "azure",
        "aws_s3", "aws_ec2", "aws_lambda", "aws_rds",
        "google_bigquery", "google_cloud_run", "azure_functions",
        "serverless", "cloud_native",
        # Mobile
        "ios", "android", "react_native", "flutter",
        "swiftui", "mobile_development",
        # Security
        "cybersecurity", "penetration_testing", "application_security",
        "network_security", "security_operations", "devsecops",
        "owasp", "vulnerability_assessment", "cryptography",
        "identity_access_management", "zero_trust",
        # Data Engineering
        "sql", "etl", "spark", "kafka", "airflow", "hadoop",
        "data_warehousing", "data_build_tool", "data_modeling",
        "tableau", "power_bi", "looker", "dbt_core",
        # Databases
        "mysql", "postgresql", "mssql", "sqlite",
        "mongodb", "redis", "elasticsearch", "cassandra",
        "dynamodb", "neo4j", "firebase", "supabase",
        # Systems / Architecture
        "microservices", "distributed_systems", "message_queues",
        "rabbitmq", "grpc", "agile", "scrum", "jira", "system_design",
        # Languages (each appears once — no duplicate across domain lists)
        "python", "javascript", "typescript", "java", "cpp", "csharp",
        "go", "rust", "ruby", "php", "swift", "kotlin", "dart",
        "scala", "r_lang", "matlab", "bash", "objective_c",
        # Shared tools (each once)
        "linux", "git", "nodejs",
        # QA / Testing
        "software_testing", "manual_testing", "automated_testing",
        "selenium", "playwright", "cypress_testing", "pytest",
        "junit", "testng", "mocha", "jest_testing",
        "load_testing", "performance_testing", "jmeter", "k6",
        "api_testing", "postman", "rest_assured",
        "unit_testing", "integration_testing", "e2e_testing",
        "test_driven_development", "behavior_driven_development",
        "cucumber", "appium", "mobile_testing",
        "accessibility_testing", "security_testing_qa",
        # Blockchain
        "blockchain", "ethereum", "solidity", "web3",
        "smart_contracts", "defi", "nft", "hyperledger",
        "web3_js", "ethers_js", "hardhat", "truffle",
        "ipfs", "polygon", "binance_smart_chain",
        "cryptocurrency", "consensus_mechanisms",
        "zero_knowledge_proofs", "layer2_scaling",
        # Game Dev
        "game_development", "unity", "unreal_engine", "godot",
        "opengl", "vulkan", "directx", "webgl",
        "game_physics", "shader_programming", "hlsl", "glsl",
        "blender", "3d_modeling", "animation",
        "game_design", "level_design", "multiplayer_networking",
        "unity_csharp", "unreal_cpp", "procedural_generation",
        # Embedded / IoT
        "embedded_systems", "iot", "arduino", "raspberry_pi",
        "rtos", "freertos", "c_embedded", "assembly",
        "microcontrollers", "esp32", "stm32",
        "firmware_development", "hardware_programming",
        "uart", "spi", "i2c", "can_bus",
        "edge_computing", "mqtt", "zigbee", "bluetooth_le",
        "sensor_integration", "plc_programming",
        # Research
        "research_skills", "latex", "matlab_research", "r_statistics",
        "jupyter", "academic_writing", "data_analysis",
        "statistical_analysis", "hypothesis_testing",
        "literature_review", "scientific_computing",
        "numpy_research", "scipy", "spss", "stata",
        "research_methodology", "experiment_design",
        "technical_writing", "paper_writing", "ieee_formatting",
    ]

    for node in skill_nodes:
        G.add_node(node)

    # ── CHILD_OF edges (parent → child means child is a specialization) ────────
    child_of_edges = [
        # AI hierarchy
        ("artificial_intelligence", "machine_learning"),
        ("artificial_intelligence", "computer_vision"),
        ("artificial_intelligence", "natural_language_processing"),
        ("artificial_intelligence", "reinforcement_learning"),
        ("artificial_intelligence", "generative_ai"),
        ("machine_learning", "deep_learning"),
        ("machine_learning", "scikit_learn"),
        ("machine_learning", "xgboost"),
        ("machine_learning", "lightgbm"),
        ("deep_learning", "computer_vision"),
        ("deep_learning", "natural_language_processing"),
        ("deep_learning", "generative_adversarial_networks"),
        ("deep_learning", "tensorflow"),
        ("deep_learning", "pytorch"),
        ("deep_learning", "keras"),
        ("natural_language_processing", "bert"),
        ("natural_language_processing", "transformers_lib"),
        ("natural_language_processing", "nltk"),
        ("natural_language_processing", "spacy"),
        ("generative_ai", "large_language_models"),
        ("generative_ai", "stable_diffusion"),
        ("generative_ai", "generative_adversarial_networks"),
        ("large_language_models", "huggingface"),
        ("large_language_models", "langchain"),
        ("large_language_models", "llamaindex"),
        ("large_language_models", "retrieval_augmented_generation"),
        ("computer_vision", "opencv"),

        # Web hierarchy
        ("javascript", "typescript"),
        ("javascript", "react"),
        ("javascript", "vue"),
        ("javascript", "angular"),
        ("javascript", "svelte"),
        ("javascript", "nodejs"),
        ("javascript", "jest"),
        ("nodejs", "express"),
        ("react", "nextjs"),
        ("vue", "nuxtjs"),
        ("python", "fastapi"),
        ("python", "flask"),
        ("python", "django"),
        ("ruby", "rails"),
        ("css", "sass"),
        ("css", "tailwindcss"),
        ("css", "bootstrap"),

        # DevOps hierarchy
        ("docker", "kubernetes"),
        ("cicd", "github_actions"),
        ("cicd", "gitlab_cicd"),
        ("cicd", "jenkins"),
        ("iac", "terraform"),
        ("iac", "ansible"),
        ("kubernetes", "helm"),
        ("prometheus", "grafana"),

        # Cloud hierarchy
        ("amazon_web_services", "aws_s3"),
        ("amazon_web_services", "aws_ec2"),
        ("amazon_web_services", "aws_lambda"),
        ("amazon_web_services", "aws_rds"),
        ("google_cloud", "google_bigquery"),
        ("google_cloud", "google_cloud_run"),
        ("azure", "azure_functions"),
        ("aws_lambda", "serverless"),
        ("google_cloud_run", "serverless"),
        ("azure_functions", "serverless"),

        # Mobile hierarchy
        ("mobile_development", "ios"),
        ("mobile_development", "android"),
        ("mobile_development", "react_native"),
        ("mobile_development", "flutter"),
        ("ios", "swift"),
        ("ios", "swiftui"),
        ("ios", "objective_c"),
        ("android", "kotlin"),
        ("flutter", "dart"),

        # Security hierarchy
        ("cybersecurity", "penetration_testing"),
        ("cybersecurity", "application_security"),
        ("cybersecurity", "network_security"),
        ("cybersecurity", "security_operations"),
        ("cybersecurity", "devsecops"),
        ("cybersecurity", "identity_access_management"),
        ("cybersecurity", "zero_trust"),
        ("penetration_testing", "vulnerability_assessment"),
        ("application_security", "owasp"),

        # Data Engineering hierarchy
        ("etl", "spark"),
        ("etl", "kafka"),
        ("etl", "airflow"),
        ("etl", "hadoop"),
        ("data_warehousing", "data_build_tool"),
        ("data_warehousing", "data_modeling"),
        ("data_warehousing", "google_bigquery"),
        ("data_build_tool", "dbt_core"),

        # Database hierarchy
        ("sql", "mysql"),
        ("sql", "postgresql"),
        ("sql", "mssql"),
        ("sql", "sqlite"),

        # Systems hierarchy
        ("distributed_systems", "microservices"),
        ("distributed_systems", "message_queues"),
        ("message_queues", "rabbitmq"),
        ("message_queues", "kafka"),

        # QA/Testing hierarchy
        ("software_testing", "manual_testing"),
        ("software_testing", "automated_testing"),
        ("software_testing", "performance_testing"),
        ("software_testing", "api_testing"),
        ("software_testing", "mobile_testing"),
        ("software_testing", "security_testing_qa"),
        ("automated_testing", "selenium"),
        ("automated_testing", "playwright"),
        ("automated_testing", "cypress_testing"),
        ("automated_testing", "appium"),
        ("automated_testing", "test_driven_development"),
        ("automated_testing", "behavior_driven_development"),
        ("behavior_driven_development", "cucumber"),
        ("performance_testing", "load_testing"),
        ("performance_testing", "jmeter"),
        ("performance_testing", "k6"),
        ("api_testing", "postman"),
        ("api_testing", "rest_assured"),
        ("software_testing", "unit_testing"),
        ("software_testing", "integration_testing"),
        ("software_testing", "e2e_testing"),
        ("software_testing", "accessibility_testing"),
        ("unit_testing", "pytest"),
        ("unit_testing", "junit"),
        ("unit_testing", "testng"),
        ("unit_testing", "mocha"),
        ("unit_testing", "jest_testing"),

        # Blockchain hierarchy
        ("blockchain", "ethereum"),
        ("blockchain", "hyperledger"),
        ("blockchain", "defi"),
        ("blockchain", "nft"),
        ("blockchain", "consensus_mechanisms"),
        ("blockchain", "zero_knowledge_proofs"),
        ("blockchain", "layer2_scaling"),
        ("ethereum", "solidity"),
        ("ethereum", "smart_contracts"),
        ("ethereum", "web3"),
        ("ethereum", "polygon"),
        ("web3", "web3_js"),
        ("web3", "ethers_js"),
        ("smart_contracts", "hardhat"),
        ("smart_contracts", "truffle"),
        ("defi", "binance_smart_chain"),
        ("blockchain", "ipfs"),
        ("blockchain", "cryptocurrency"),

        # Game Dev hierarchy
        ("game_development", "unity"),
        ("game_development", "unreal_engine"),
        ("game_development", "godot"),
        ("game_development", "game_design"),
        ("game_development", "level_design"),
        ("game_development", "multiplayer_networking"),
        ("game_development", "procedural_generation"),
        ("game_development", "3d_modeling"),
        ("game_development", "animation"),
        ("unity", "unity_csharp"),
        ("unreal_engine", "unreal_cpp"),
        ("opengl", "vulkan"),
        ("opengl", "webgl"),
        ("opengl", "directx"),
        ("shader_programming", "hlsl"),
        ("shader_programming", "glsl"),
        ("3d_modeling", "blender"),

        # Embedded/IoT hierarchy
        ("embedded_systems", "firmware_development"),
        ("embedded_systems", "hardware_programming"),
        ("embedded_systems", "microcontrollers"),
        ("embedded_systems", "rtos"),
        ("embedded_systems", "c_embedded"),
        ("embedded_systems", "assembly"),
        ("iot", "arduino"),
        ("iot", "raspberry_pi"),
        ("iot", "esp32"),
        ("iot", "edge_computing"),
        ("iot", "sensor_integration"),
        ("iot", "mqtt"),
        ("iot", "zigbee"),
        ("iot", "bluetooth_le"),
        ("rtos", "freertos"),
        ("microcontrollers", "stm32"),
        ("microcontrollers", "esp32"),
        ("hardware_programming", "uart"),
        ("hardware_programming", "spi"),
        ("hardware_programming", "i2c"),
        ("hardware_programming", "can_bus"),
        ("embedded_systems", "plc_programming"),

        # Research hierarchy
        ("research_skills", "academic_writing"),
        ("research_skills", "research_methodology"),
        ("research_skills", "experiment_design"),
        ("research_skills", "literature_review"),
        ("research_skills", "statistical_analysis"),
        ("research_skills", "scientific_computing"),
        ("research_skills", "technical_writing"),
        ("academic_writing", "paper_writing"),
        ("academic_writing", "ieee_formatting"),
        ("academic_writing", "latex"),
        ("statistical_analysis", "hypothesis_testing"),
        ("statistical_analysis", "spss"),
        ("statistical_analysis", "stata"),
        ("statistical_analysis", "r_statistics"),
        ("scientific_computing", "matlab_research"),
        ("scientific_computing", "jupyter"),
        ("scientific_computing", "scipy"),
        ("scientific_computing", "numpy_research"),
        ("data_analysis", "r_statistics"),
        ("data_analysis", "stata"),
        ("data_analysis", "spss"),
    ]

    for parent, child in child_of_edges:
        G.add_edge(parent, child, relation="CHILD_OF")

    # ── IS_ALIAS_OF edges (from alias_table.json) ─────────────────────────────
    alias_path = ONTOLOGY_DIR / "alias_table.json"
    with open(alias_path, encoding="utf-8") as f:
        alias_table = json.load(f)

    for raw, canonical in alias_table.items():
        if raw == "_comment":
            continue
        if not G.has_node(canonical):
            G.add_node(canonical, domain="unknown")
        alias_node = f"_alias_{raw.replace(' ', '_')}"
        G.add_node(alias_node, alias_for=canonical, is_alias=True)
        G.add_edge(alias_node, canonical, relation="IS_ALIAS_OF")

    return G


def main():
    print("Building skill ontology graph...")
    G = build_graph()

    real_nodes = [n for n in G.nodes if not n.startswith("_alias_")]
    alias_nodes = [n for n in G.nodes if n.startswith("_alias_")]
    child_edges = [(u, v) for u, v, d in G.edges(data=True) if d.get("relation") == "CHILD_OF"]
    alias_edges = [(u, v) for u, v, d in G.edges(data=True) if d.get("relation") == "IS_ALIAS_OF"]

    print(f"  Skill nodes : {len(real_nodes)}")
    print(f"  Alias nodes : {len(alias_nodes)}")
    print(f"  CHILD_OF    : {len(child_edges)}")
    print(f"  IS_ALIAS_OF : {len(alias_edges)}")
    print(f"  Total nodes : {G.number_of_nodes()}")
    print(f"  Total edges : {G.number_of_edges()}")

    out_path = ONTOLOGY_DIR / "skill_ontology.gpickle"
    with open(out_path, "wb") as f:
        pickle.dump(G, f)
    print(f"\nSaved -> {out_path}")

    if len(real_nodes) >= 200 and G.number_of_edges() >= 300:
        print("PASS: graph size requirements met.")
    else:
        print("WARN: graph smaller than expected — add more nodes/edges.")


if __name__ == "__main__":
    main()

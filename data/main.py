import logging
import os
from dotenv import load_dotenv
import uvicorn
import yaml
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from mako.template import Template
from mako.lookup import TemplateLookup
from pydantic import BaseModel
from typing import Optional, Dict

# Load environment variables from .env
env_path = r"/em-etl-data/batch/config/.env"
if os.path.exists(env_path):
    load_dotenv(env_path)
else:
    logging.warning(f".env file not found at {env_path}")
# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

app = FastAPI()


class PipelineConfig(BaseModel):
    job_type: str
    edges: list
    nodes: list
    job_id: Optional[str] = None


# Read environment variables with fallbacks
TEMPLATE_PATH = os.getenv("TEMPLATE_PATH", "templates/pipeline_template.py.mako")
TEMPLATE_DIR = os.path.dirname(TEMPLATE_PATH) if os.path.exists(TEMPLATE_PATH) else "templates"
OUTPUT_SCRIPT = os.getenv("OUTPUT_SCRIPT", "generated/batch_spark_script.py")
CONFIG_FILE_PATH = os.getenv("CONFIG_FILE_PATH")  # Unused? Kept for compatibility


os.makedirs(os.path.dirname(OUTPUT_SCRIPT), exist_ok=True)  # Ensure output dir exists


def extract_minio_config_from_target(nodes: list) -> Optional[Dict]:
    """
    Extract MinIO/S3 config from target nodes.
    Maps to expected keys: endpoint, access_key, secret_key.
    """
    for node in nodes:
        if node.get('type', '').lower() == 'target' and node.get('catalog_name') in ['iceberg', 's3']:
            config = {
                'endpoint': node.get('s3_endpoint', node.get('endpoint')),
                'access_key': node.get('s3_aws_access_key', node.get('access_key')),
                'secret_key': node.get('s3_aws_secret_key', node.get('secret_key')),
                'region': node.get('s3_region', 'ap-south-1'),
                # Add more mappings as needed
            }
            if any(config.values()):  # If any key found
                logging.info(f"Extracted MinIO config from node {node.get('id')}")
                return config
    logging.warning("No MinIO/S3 target node found")
    return None


@app.post("/generate-script")
async def generate_pipeline(config: PipelineConfig):
    try:
        config_dict = config.dict()
        # Extract MinIO config
        minio_config = extract_minio_config_from_target(config_dict["nodes"])

        # Create safe Python literal for embedding config in script
        config_literal = repr(config_dict)  # e.g., "{'job_type': 'batch', ...}"

        # Build nodes/edges maps (as before)
        nodes_map = {node["id"]: node for node in config_dict["nodes"]}
        edges_map = {edge["target"]: edge["source"] for edge in config_dict["edges"]}

        # Template setup
        lookup = TemplateLookup(directories=[TEMPLATE_DIR], strict_undefined=True)
        template = lookup.get_template(os.path.basename(TEMPLATE_PATH))

        # Render with embedded config literal and function
        rendered_script = template.render(
            config=config_dict,
            config_literal=config_literal,  # For embedding as exec-able string
            minio_config=minio_config,
            extract_minio_func=extract_minio_config_from_target,  # Pass function if needed, but better inline in template
            nodes_map=nodes_map,
            edges_map=edges_map
        )

        with open(OUTPUT_SCRIPT, "w") as f:
            f.write(rendered_script)

        logging.info(f"Script generated at {OUTPUT_SCRIPT}")
        return FileResponse(
            path=OUTPUT_SCRIPT,
            filename="batch_spark_script.py",
            media_type="application/octet-stream",
        )

    except Exception as e:
        logging.error(f"An error occurred: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import os
    host = os.getenv("APP_HOST", "0.0.0.0")

    port = int(os.getenv("APP_PORT", 8005))
    reload = os.getenv("APP_RELOAD", "False").lower() == "true"
    log_level = os.getenv("APP_LOG_LEVEL", "info")
    logging.info("Starting the FastAPI app...")
    uvicorn.run("main:app", host=host, port=port, reload=reload, log_level=log_level)

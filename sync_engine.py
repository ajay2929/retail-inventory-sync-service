import asyncio
import logging
import httpx
from motor.motor_asyncio import AsyncIOMotorClient
from datetime import datetime

# 1. Professional Logging Setup
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

class InventorySyncEngine:
    """
    A senior-level sync engine showcasing async patterns and resilience.
    Reflects experience in E-Commerce Integration.
    """
    def __init__(self, erp_url: str, db_uri: str):
        self.erp_url = erp_url
        self.client = AsyncIOMotorClient(db_uri)
        self.db = self.client.inventory_db
        self.collection = self.db.products

    async def fetch_erp_data(self, product_id: str):
        """Fetch data with a focus on non-blocking I/O and error handling."""
        async with httpx.AsyncClient() as client:
            try:
                logger.info(f"Fetching data for Product ID: {product_id}")
                response = await client.get(f"{self.erp_url}/products/{product_id}", timeout=10.0)
                response.raise_for_status()
                return response.json()
            except httpx.HTTPStatusError as e:
                logger.error(f"ERP Error: {e.response.status_code} for Product {product_id}")
                return None
            except Exception as e:
                logger.error(f"Unexpected connection error: {str(e)}")
                return None

    async def sync_product(self, product_id: str):
        """Implements the Transform and Load (TL) of the ETL process."""
        raw_data = await self.fetch_erp_data(product_id)
        
        if not raw_data:
            return

        # Data Transformation (Standardizing Legacy Data)
        transformed_data = {
            "sku": raw_data.get("legacy_sku"),
            "stock_level": raw_data.get("qty", 0),
            "last_sync": datetime.utcnow(),
            "status": "active" if raw_data.get("qty", 0) > 0 else "out_of_stock"
        }

        # Atomic Upsert in MongoDB
        result = await self.collection.update_one(
            {"sku": transformed_data["sku"]},
            {"$set": transformed_data},
            upsert=True
        )
        logger.info(f"Successfully synced SKU: {transformed_data['sku']}")

async def main():
    # Example usage (Using placeholder URLs)
    engine = InventorySyncEngine(
        erp_url="https://api.legacy-erp.com/v1", 
        db_uri="mongodb://localhost:27017"
    )
    
    # Simulating a batch sync
    product_ids = ["PROD-001", "PROD-002", "PROD-003"]
    tasks = [engine.sync_product(pid) for pid in product_ids]
    await asyncio.gather(*tasks)

if __name__ == "__main__":
    asyncio.run(main())

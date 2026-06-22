import json
import logging
from typing import Dict, Any

from .base import BaseAgent
from ..config import MOCK_MODE, OCS_SEARCH_URL, OCS_CONFIG_URL, OCS_INDEXER_URL

class FixVerificationAgent(BaseAgent):
    """
    Sub-agent 1: FixVerificationAgent
    Verifies that the fixes planned by FixPlanAgent were applied correctly.
    Checks:
      1. Query returns results (POST /search-api/v1/search)
      2. Searchable fields applied in config (GET /config-service/v1/index-config)
      3. Synonym mappings active (GET /suggest-service/v1/suggest or query expansion check)
      4. Embedding refresh completed (GET /indexer-service/v1/status)
      5. Merchandising rules applied in search (GET /search-api/v1/rules/active)
    """

    def run(self, input_data: Dict[str, Any], pipeline_state: Dict[str, Any]) -> Dict[str, Any]:
        self.logger.info("Starting fix verification check...")
        
        result_wrapper = input_data.get("result", {})
        apply_result = result_wrapper.get("applyResult", {})
        
        # Check if the fix was applied at all
        if not apply_result.get("applied", False):
            self.logger.error("Fix was not applied (applyResult.applied = False).")
            return {
                "verification": {
                    "allPassed": False,
                    "checks": [],
                    "error": "Fix application failed upstream (applyResult.applied is false)."
                }
            }

        query = input_data.get("query") or result_wrapper.get("query", "")
        catalog_patch = result_wrapper.get("catalogPatch", {})
        autocomplete_patch = result_wrapper.get("autocompletePatch", {})
        embedding_patch = result_wrapper.get("embeddingPatch", {})
        merchandising_patch = result_wrapper.get("merchandisingPatch", {})

        checks = []
        all_passed = True

        # Check 1: Query returns results
        check_query = self._verify_query_returns_results(query)
        checks.append(check_query)
        if not check_query["passed"]:
            all_passed = False

        # Check 2: Searchable fields applied
        check_fields = self._verify_searchable_fields(catalog_patch)
        checks.append(check_fields)
        if not check_fields["passed"]:
            all_passed = False

        # Check 3: Synonyms active
        check_synonyms = self._verify_synonyms_active(autocomplete_patch)
        checks.append(check_synonyms)
        if not check_synonyms["passed"]:
            all_passed = False

        # Check 4: Embeddings refreshed
        check_embeddings = self._verify_embeddings_refreshed(embedding_patch)
        checks.append(check_embeddings)
        if not check_embeddings["passed"]:
            all_passed = False

        # Check 5: Merchandising rules applied
        check_rules = self._verify_merchandising_rules(merchandising_patch)
        checks.append(check_rules)
        if not check_rules["passed"]:
            all_passed = False

        verification_report = {
            "allPassed": all_passed,
            "checks": checks
        }

        self.logger.info(f"Fix verification completed. allPassed={all_passed}")
        return {"verification": verification_report}

    def _verify_query_returns_results(self, query: str) -> Dict[str, Any]:
        self.logger.info(f"Verifying results for query: '{query}'")
        if MOCK_MODE:
            # Simulate OCS Search API response. The expected outcome is positive results (e.g. 3)
            return {
                "name": "query_returns_results",
                "passed": True,
                "resultCount": 3,
                "details": f"Simulated: Query '{query}' successfully returned 3 results (expected lift from 0)."
            }
        else:
            import requests
            try:
                # Actual OCS Search API call
                url = f"{OCS_SEARCH_URL}/search-api/v1/search"
                response = requests.post(url, json={"q": query}, timeout=5)
                if response.status_code == 200:
                    data = response.json()
                    # OCS returns results in list 'results' or similar
                    results = data.get("results", [])
                    result_count = len(results)
                    return {
                        "name": "query_returns_results",
                        "passed": result_count > 0,
                        "resultCount": result_count,
                        "details": f"OCS Search API returned {result_count} items."
                    }
                else:
                    return {
                        "name": "query_returns_results",
                        "passed": False,
                        "resultCount": 0,
                        "details": f"OCS Search API responded with status {response.status_code}."
                    }
            except Exception as e:
                self.logger.exception("Failed to query OCS Search API:")
                return {
                    "name": "query_returns_results",
                    "passed": False,
                    "resultCount": 0,
                    "details": f"Connection error: {str(e)}"
                }

    def _verify_searchable_fields(self, catalog_patch: Dict[str, Any]) -> Dict[str, Any]:
        fields_to_add = catalog_patch.get("searchableFields", {}).get("add", [])
        self.logger.info(f"Verifying searchable fields added: {fields_to_add}")
        
        if MOCK_MODE:
            return {
                "name": "searchable_fields_applied",
                "passed": True,
                "fieldsAdded": len(fields_to_add),
                "details": f"Simulated: Verified that {fields_to_add} are active in Config Service and search index mapping."
            }
        else:
            import requests
            try:
                # Actual OCS Config API call
                url = f"{OCS_CONFIG_URL}/config-service/v1/index-config"
                response = requests.get(url, timeout=5)
                if response.status_code == 200:
                    config = response.json()
                    current_searchable = config.get("searchableFields", [])
                    # Verify all planned fields are present in the remote config
                    missing = [f for f in fields_to_add if f not in current_searchable]
                    if not missing:
                        return {
                            "name": "searchable_fields_applied",
                            "passed": True,
                            "fieldsAdded": len(fields_to_add),
                            "details": f"Verified fields {fields_to_add} are active in Config Service."
                        }
                    else:
                        return {
                            "name": "searchable_fields_applied",
                            "passed": False,
                            "fieldsAdded": len(fields_to_add) - len(missing),
                            "details": f"Missing searchable fields in active configuration: {missing}"
                        }
                else:
                    return {
                        "name": "searchable_fields_applied",
                        "passed": False,
                        "fieldsAdded": 0,
                        "details": f"OCS Config Service responded with status {response.status_code}."
                    }
            except Exception as e:
                self.logger.exception("Failed to query OCS Config Service:")
                return {
                    "name": "searchable_fields_applied",
                    "passed": False,
                    "fieldsAdded": 0,
                    "details": f"Connection error: {str(e)}"
                }

    def _verify_synonyms_active(self, autocomplete_patch: Dict[str, Any]) -> Dict[str, Any]:
        mappings = autocomplete_patch.get("synonymMappings", [])
        self.logger.info(f"Verifying synonym mappings active: {len(mappings)} mappings")
        
        if MOCK_MODE:
            return {
                "name": "synonyms_active",
                "passed": True,
                "mappingsVerified": len(mappings),
                "details": f"Simulated: Verified {len(mappings)} synonym mappings in Querqy configuration."
            }
        else:
            import requests
            try:
                # We can query OCS Suggest or Search service rules endpoint
                # Typically synonyms in OCS are handled via Querqy rules or Config Service
                url = f"{OCS_CONFIG_URL}/config-service/v1/synonyms"
                response = requests.get(url, timeout=5)
                if response.status_code == 200:
                    active_synonyms = response.json() # list or map of synonyms
                    # Simple heuristic match or lookup
                    passed_count = 0
                    for mapping in mappings:
                        term = mapping.get("term")
                        # Check if term exists in configured synonyms
                        if term in active_synonyms or any(term == entry.get("term") for entry in active_synonyms if isinstance(entry, dict)):
                            passed_count += 1
                    
                    return {
                        "name": "synonyms_active",
                        "passed": passed_count == len(mappings),
                        "mappingsVerified": passed_count,
                        "details": f"Verified {passed_count}/{len(mappings)} synonym mappings in configuration."
                    }
                else:
                    return {
                        "name": "synonyms_active",
                        "passed": False,
                        "mappingsVerified": 0,
                        "details": f"OCS Synonyms Config responded with status {response.status_code}."
                    }
            except Exception as e:
                self.logger.exception("Failed to query OCS Synonym Config:")
                return {
                    "name": "synonyms_active",
                    "passed": False,
                    "mappingsVerified": 0,
                    "details": f"Connection error: {str(e)}"
                }

    def _verify_embeddings_refreshed(self, embedding_patch: Dict[str, Any]) -> Dict[str, Any]:
        product_ids = embedding_patch.get("affectedProductIds", [])
        self.logger.info(f"Verifying embedding refresh for product IDs: {product_ids}")
        
        if MOCK_MODE:
            return {
                "name": "embedding_refreshed",
                "passed": True,
                "productsRefreshed": len(product_ids),
                "details": f"Simulated: Verified that vector embeddings for {product_ids} were refreshed in Indexer."
            }
        else:
            import requests
            try:
                # Contact Indexer Service to check status of embedding indexing
                # We query status for product IDs
                passed_count = 0
                for pid in product_ids:
                    url = f"{OCS_INDEXER_URL}/indexer-service/v1/status/{pid}"
                    response = requests.get(url, timeout=5)
                    if response.status_code == 200:
                        status = response.json()
                        # check if embedding timestamp matches or status is INDEXED
                        if status.get("embeddingStatus") == "INDEXED" or status.get("status") == "SUCCESS":
                            passed_count += 1
                
                return {
                    "name": "embedding_refreshed",
                    "passed": passed_count == len(product_ids),
                    "productsRefreshed": passed_count,
                    "details": f"Verified {passed_count}/{len(product_ids)} products successfully re-embedded."
                }
            except Exception as e:
                self.logger.exception("Failed to query Indexer status:")
                return {
                    "name": "embedding_refreshed",
                    "passed": False,
                    "productsRefreshed": 0,
                    "details": f"Connection error: {str(e)}"
                }

    def _verify_merchandising_rules(self, merchandising_patch: Dict[str, Any]) -> Dict[str, Any]:
        rules = merchandising_patch.get("rules", [])
        self.logger.info(f"Verifying merchandising rules active: {len(rules)} rules")
        
        if MOCK_MODE:
            return {
                "name": "merchandising_rules_applied",
                "passed": True,
                "rulesApplied": len(rules),
                "details": f"Simulated: Verified {len(rules)} rules are active in search-service rule-engine."
            }
        else:
            import requests
            try:
                # Fetch active Querqy rules from Search API rule mapping endpoint
                url = f"{OCS_SEARCH_URL}/search-api/v1/rules/active"
                response = requests.get(url, timeout=5)
                if response.status_code == 200:
                    active_rules = response.json() # list or map
                    # verify rules exist in active rule mapping
                    passed_count = 0
                    for r in rules:
                        rule_id = r.get("id")
                        if any(rule_id == active_r.get("id") for active_r in active_rules if isinstance(active_r, dict)):
                            passed_count += 1
                    
                    return {
                        "name": "merchandising_rules_applied",
                        "passed": passed_count == len(rules),
                        "rulesApplied": passed_count,
                        "details": f"Verified {passed_count}/{len(rules)} rules applied in Querqy engine."
                    }
                else:
                    return {
                        "name": "merchandising_rules_applied",
                        "passed": False,
                        "rulesApplied": 0,
                        "details": f"OCS Rule Engine status returned code {response.status_code}."
                    }
            except Exception as e:
                self.logger.exception("Failed to verify merchandising rules:")
                return {
                    "name": "merchandising_rules_applied",
                    "passed": False,
                    "rulesApplied": 0,
                    "details": f"Connection error: {str(e)}"
                }

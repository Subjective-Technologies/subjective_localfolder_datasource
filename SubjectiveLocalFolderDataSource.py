from subjective_abstract_data_source_package import SubjectiveDataSource
from brainboost_data_source_logger_package.BBLogger import BBLogger

class SubjectiveLocalFolderDataSource(SubjectiveDataSource):

    def __init__(self, params=None):
        super().__init__(params=params)
        params = params or {}
        self.time_interval = params.get('time_interval', 5)

    def fetch(self):
        # This code will take screenshots and extract KnowledgeHooks
        BBLogger.log("Starting real-time KnowledgeHooks processing.")
        # [Your real-time fetching implementation here]
        payload = {
            "type": "local_folder_start",
            "path": self.params.get("path", ""),
            "connection_name": self.params.get("connection_name", ""),
            "server": self.params.get("server", ""),
        }
        return payload

    # ------------------ New Methods ------------------
    def get_icon(self):
        """Return SVG icon content, preferring a local icon.svg in the plugin folder."""
        import os
        icon_path = os.path.join(os.path.dirname(__file__), 'icon.svg')
        try:
            if os.path.exists(icon_path):
                with open(icon_path, 'r', encoding='utf-8') as f:
                    return f.read()
        except Exception:
            pass
        return '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><rect width="24" height="24" rx="4" fill="#f59e0b"/><path fill="#fff" d="M6 7h12v2H6zm0 4h12v2H6zm0 4h8v2H6z"/></svg>'

    def get_connection_data(self):
        """
        Return the connection type and required fields for KnowledgeHooks real-time data.
        """
        return {
            "connection_type": "LocalFolder",
            "fields": ["path", "time_interval"]
        }


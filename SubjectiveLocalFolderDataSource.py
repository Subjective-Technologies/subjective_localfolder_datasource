from subjective_abstract_data_source_package import SubjectiveDataSource
from brainboost_data_source_logger_package.BBLogger import BBLogger

class SubjectiveLocalFolderDataSource(SubjectiveDataSource):

    def __init__(self, params=None):
        super().__init__(params=params)
        self.time_interval = params['time_interval']

    def fetch(self):
        # This code will take screenshots and extract KnowledgeHooks
        BBLogger.log("Starting real-time KnowledgeHooks processing.")
        # [Your real-time fetching implementation here]
        pass

    # ------------------ New Methods ------------------
    def get_icon(self):
        """Return the SVG code for the KnowledgeHooks (Real Time) icon."""
        return """<svg viewBox="0 0 1024 1024" class="icon" version="1.1" xmlns="http://www.w3.org/2000/svg" fill="#000000"><g id="SVGRepo_bgCarrier" stroke-width="0"></g><g id="SVGRepo_tracerCarrier" stroke-linecap="round" stroke-linejoin="round"></g><g id="SVGRepo_iconCarrier"><path d="M853.333333 256H469.333333l-85.333333-85.333333H170.666667c-46.933333 0-85.333333 38.4-85.333334 85.333333v170.666667h853.333334v-85.333334c0-46.933333-38.4-85.333333-85.333334-85.333333z" fill="#FFA000"></path><path d="M853.333333 256H170.666667c-46.933333 0-85.333333 38.4-85.333334 85.333333v426.666667c0 46.933333 38.4 85.333333 85.333334 85.333333h682.666666c46.933333 0 85.333333-38.4 85.333334-85.333333V341.333333c0-46.933333-38.4-85.333333-85.333334-85.333333z" fill="#FFCA28"></path></g></svg>"""

    def get_connection_data(self):
        """
        Return the connection type and required fields for KnowledgeHooks real-time data.
        """
        return {
            "connection_type": "LocalFolder",
            "fields": ["path"]
        }


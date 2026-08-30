from app.models.scanning import ScannerEvidence
from app.tools.gateway import ToolGateway
from app.tools.scanners import ScannerSuite


class ExternalValidationService:
    def __init__(
        self,
        gateway: ToolGateway | None = None,
        scanners: ScannerSuite | None = None,
    ) -> None:
        self.gateway = gateway or ToolGateway()
        self.scanners = scanners or ScannerSuite()

    def run(self, task_id: str) -> list[ScannerEvidence]:
        workspace = self.gateway.workspace_for(task_id)
        return self.scanners.run_all(workspace)

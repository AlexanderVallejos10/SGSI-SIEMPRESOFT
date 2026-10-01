import tempfile
from unittest import mock

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings

from apps.context41.models import ContextDocument, ContextDocumentVersion, LegalRequirement
from apps.context41.services import ensure_source_artifact_from_upload, import_legal_rows


def fila(n, estado="Vigente"):
    return {"source_row": n, "number": n, "requirement": f"Requisito {n}", "promulgated_by": "SUNAT", "location": "",
            "responsible": "Oficial de Seguridad", "interested_parties": "", "status": estado}


@override_settings(MEDIA_ROOT=tempfile.mkdtemp(prefix="sgsi-test-41-"))
class ReimportarRequisitosLegales(TestCase):
    def setUp(self):
        artifact = ensure_source_artifact_from_upload(SimpleUploadedFile("requisitos.xlsx", b"contenido-de-prueba"))
        document = ContextDocument.objects.create(slug="requisitos-legales", title="Requisitos legales")
        self.version = ContextDocumentVersion.objects.create(document=document, version_label="V0.15", source_artifact=artifact,
                                                             original_name="requisitos.xlsx")

    def test_volver_a_importar_no_borra_ni_duplica(self):
        with mock.patch("apps.context41.services.parse_legal_requirements", return_value=[fila(1), fila(2)]):
            import_legal_rows(self.version)
        ids = set(LegalRequirement.objects.filter(version=self.version).values_list("pk", flat=True))
        with mock.patch("apps.context41.services.parse_legal_requirements", return_value=[fila(1), fila(2, "Derogado")]):
            import_legal_rows(self.version)
        rows = LegalRequirement.objects.filter(version=self.version)
        self.assertEqual(set(rows.values_list("pk", flat=True)), ids)
        self.assertEqual(rows.get(source_row=2).status, "Derogado")

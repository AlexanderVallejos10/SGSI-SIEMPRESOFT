from django.test import SimpleTestCase

from apps.documents.management.commands.import_source_inventory import secret_reason


class FiltroDeSecretos(SimpleTestCase):
    def test_omite_llaves_y_claves(self):
        for path in [
            "06 - Área de Producción/03 - Infraestructura Tecnológica/Registros/Certificados SMIME/Fase IV/ksalazar.p12",
            "06 - Área de Producción/03 - Infraestructura Tecnológica/Restringida/Documentos no vigentes/Claves de recuperación Bitlocker - NO VIGENTE/CPU002c.TXT",
            "06 - Área de Producción/03 - Infraestructura Tecnológica/Registros/Certificados VPN/2024/JoseTorres_2024.zip",
            "02 - Área de Seguridad de la Información/Registros/Claves SSH - Ubuntu demo/TMP-BI_key.zip",
            "06 - Área de Producción/03 - Infraestructura Tecnológica/Restringida/Documentos vigentes/Herramientas Producción - Instalación/CertificadoSSLWildcard_2020_2021.zip",
            "02 - Área de Seguridad de la Información/Registros/LOG Gestión de Claves/Registro de cambio de claves.xlsx",
        ]:
            with self.subTest(path=path):
                self.assertTrue(secret_reason(path))

    def test_no_bloquea_documentos(self):
        for path in [
            "02 - Área de Seguridad de la Información/Anexos/Instructivos/06 - Instructivo Cifrado de Unidades de Disco con BitLocker en Windows 10 Pro for Workstations.pdf",
            "02 - Área de Seguridad de la Información/Anexos/Instructivos/07 - Instructivo Certificado SSL para protocolo HTTPS en servidores SAAS asignados al dominio siempresoft.com.pdf",
            "01 - Siempresoft/Restringida/Documentos vigentes/Certificado SMC 2025 - 2028/CERT_CI_4709.pdf",
            "05 - Área de Desarrollo/02 - Programación/Restringida/Documentos vigentes/02 - Politica_de_desarrollo_seguro_V0.9.pdf",
            "07 - Área de Administración/01 - Recursos Humanos/Uso interno/Documentos vigentes/ORGANIGRAMA V. 21.pdf",
            "02 - Área de Seguridad de la Información/Uso interno/Documentos vigentes/08 - Politica_de_claves_V0.8.pdf",
        ]:
            with self.subTest(path=path):
                self.assertEqual(secret_reason(path), "")

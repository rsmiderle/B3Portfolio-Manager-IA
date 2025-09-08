import os
import sys
import unittest
import hashlib

# Adicionar o diretório raiz ao path para importar os módulos corretamente
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.main import create_app
from src.models import db
from src.models.user import User

class TestSecurityAndUserModel(unittest.TestCase):
    """Testes para validar a segurança e a criação de usuários"""

    def setUp(self):
        """Configuração inicial para cada teste"""
        os.environ['FLASK_ENV'] = 'testing'
        # Limpar a variável de ambiente do salt antes de cada teste
        if 'ANONYMIZATION_SALT' in os.environ:
            del os.environ['ANONYMIZATION_SALT']

        self.app = create_app()
        self.app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        self.app.config['TESTING'] = True
        self.app.config['WTF_CSRF_ENABLED'] = False

        self.app_context = self.app.app_context()
        self.app_context.push()

        db.create_all()

    def tearDown(self):
        """Limpeza após cada teste"""
        db.session.remove()
        db.drop_all()
        self.app_context.pop()
        # Garantir que a variável de ambiente seja limpa após os testes
        if 'ANONYMIZATION_SALT' in os.environ:
            del os.environ['ANONYMIZATION_SALT']

    def test_user_creation_fails_without_salt(self):
        """Testa se a criação de usuário falha se ANONYMIZATION_SALT não estiver definido"""
        with self.assertRaises(ValueError) as context:
            User(google_id='123', email='test@test.com')

        self.assertIn('ANONYMIZATION_SALT não está definida', str(context.exception))

    def test_user_creation_fails_with_default_insecure_salt(self):
        """Testa se a criação de usuário falha se ANONYMIZATION_SALT for o valor padrão inseguro"""
        os.environ['ANONYMIZATION_SALT'] = 'DEFAULT_SALT_CHANGE_IN_PRODUCTION'
        with self.assertRaises(ValueError) as context:
            User(google_id='123', email='test@test.com')

        self.assertIn('usando o valor padrão inseguro', str(context.exception))

    def test_user_creation_succeeds_with_valid_salt(self):
        """Testa se a criação de usuário funciona com um ANONYMIZATION_SALT válido"""
        salt = 'a_secure_random_salt_value'
        os.environ['ANONYMIZATION_SALT'] = salt

        user = User(
            google_id='user_google_id_123',
            email='secure@example.com',
            name='Secure User'
        )

        db.session.add(user)
        db.session.commit()

        # Verificar se o hash_id foi gerado
        self.assertIsNotNone(user.hash_id)
        self.assertEqual(len(user.hash_id), 64) # SHA-256 em hexadecimal

        # Verificar se o hash_id corresponde ao esperado
        expected_hash_input = f"{user.google_id}{salt}"
        expected_hash = hashlib.sha256(expected_hash_input.encode()).hexdigest()
        self.assertEqual(user.hash_id, expected_hash)

if __name__ == '__main__':
    unittest.main()

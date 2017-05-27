# -*- coding: utf-8 -*-

import unittest
from datetime import datetime

import requests_mock

import cartolafc
from cartolafc.api import MERCADO_ABERTO
from cartolafc.models import Atleta, Clube, Liga, LigaPatrocinador, Mercado, PontuacaoInfo, Time, TimeInfo
from cartolafc.models import _atleta_status, _posicoes


class ApiAttemptsTest(unittest.TestCase):
    def test_api_attempts_nao_inteiro(self):
        # Arrange and Act
        api = cartolafc.Api(attempts='texto')

        # Assert
        self.assertEqual(api.attempts, 1)

    def test_api_attempts_menor_que_1(self):
        # Arrange and Act
        api = cartolafc.Api(attempts=0)

        # Assert
        self.assertEqual(api.attempts, 1)

    def test_api_attempts(self):
        # Arrange and Act
        with requests_mock.mock() as m:
            api = cartolafc.Api(attempts=2)

            url = '{api_url}/mercado/status'.format(api_url=api._api_url)
            error_message = 'Mensagem de erro'
            m.get(url, status_code=200, text='{"mensagem": "%s"}' % error_message)

            with self.assertRaisesRegexp(cartolafc.CartolaFCError, error_message):
                api.mercado()


class ApiAuthComErro(unittest.TestCase):
    def test_api_auth_sem_email(self):
        # Act and Assert
        with self.assertRaisesRegexp(cartolafc.CartolaFCError, 'E-mail ou senha ausente'):
            cartolafc.Api(password='s3nha')

    def test_api_auth_sem_password(self):
        # Act and Assert
        with self.assertRaisesRegexp(cartolafc.CartolaFCError, 'E-mail ou senha ausente'):
            cartolafc.Api(email='email@email.com')

    def test_api_auth_invalida(self):
        # Arrange
        with requests_mock.mock() as m:
            user_message = 'Seu e-mail ou senha estao incorretos.'
            m.post('https://login.globo.com/api/authentication', status_code=401,
                   text='{"id": "BadCredentials", "userMessage": "%s"}' % user_message)

            # Act and Assert
            with self.assertRaisesRegexp(cartolafc.CartolaFCError, user_message):
                cartolafc.Api(email='email@email.com', password='s3nha')

    def test_api_auth_com_sucesso(self):
        # Arrange
        with requests_mock.mock() as m:
            m.post('https://login.globo.com/api/authentication',
                   text='{"id": "Authenticated", "userMessage": "Usuario autenticado com sucesso", "glbId": "GLB_ID"}')

            # Act
            api = cartolafc.Api(email='email@email.com', password='s3nha')

            # Assert
            self.assertEqual(api._glb_id, 'GLB_ID')

    def test_api_auth_unauthorized(self):
        # Arrange
        with requests_mock.mock() as m:
            m.post('https://login.globo.com/api/authentication',
                   text='{"id": "Authenticated", "userMessage": "Usuario autenticado com sucesso", "glbId": "GLB_ID"}')

            api = cartolafc.Api(email='email@email.com', password='s3nha')

            url = '{api_url}/mercado/status'.format(api_url=api._api_url)
            m.get(url, status_code=401)

            # Act and Assert
            with self.assertRaises(cartolafc.CartolaFCOverloadError):
                api.mercado()


class ApiAuthTest(unittest.TestCase):
    with open('testdata/amigos.json', 'rb') as f:
        AMIGOS = f.read().decode('utf8')
    with open('testdata/pontuacao_atleta.json', 'rb') as f:
        PONTUACAO_ATLETA = f.read().decode('utf8')
    with open('testdata/time_logado.json', 'rb') as f:
        TIME_LOGADO = f.read().decode('utf8')

    def setUp(self):
        with requests_mock.mock() as m:
            m.post('https://login.globo.com/api/authentication',
                   text='{"id": "Authenticated", "userMessage": "Usuario autenticado com sucesso", "glbId": "GLB_ID"}')

            self.api = cartolafc.Api(email='email@email.com', password='s3nha')
            self.api_url = self.api._api_url

    def test_amigos(self):
        # Arrange and Act
        with requests_mock.mock() as m:
            url = '{api_url}/auth/amigos'.format(api_url=self.api_url)
            m.get(url, text=self.AMIGOS)
            amigos = self.api.amigos()
            primeiro_time = amigos[0]

            # Assert
            self.assertIsInstance(amigos, list)
            self.assertIsInstance(primeiro_time, TimeInfo)
            self.assertEqual(primeiro_time.id, 22463)
            self.assertEqual(primeiro_time.nome, u'UNIÃO BRUNÃO F.C')
            self.assertEqual(primeiro_time.nome_cartola, 'Bruno Nascimento')
            self.assertEqual(primeiro_time.slug, 'uniao-brunao-f-c')
            self.assertFalse(primeiro_time.assinante)

    def test_pontuacao_atleta(self):
        # Arrange and Act
        with requests_mock.mock() as m:
            url = '{api_url}/auth/mercado/atleta/{id}/pontuacao'.format(api_url=self.api_url, id=81682)
            m.get(url, text=self.PONTUACAO_ATLETA)
            pontuacoes = self.api.pontuacao_atleta(81682)
            primeira_rodada = pontuacoes[0]

            # Assert
            self.assertIsInstance(pontuacoes, list)
            self.assertIsInstance(primeira_rodada, PontuacaoInfo)
            self.assertEqual(primeira_rodada.atleta_id, 81682)
            self.assertEqual(primeira_rodada.rodada_id, 1)
            self.assertEqual(primeira_rodada.pontos, 1.1)
            self.assertEqual(primeira_rodada.preco, 6.44)
            self.assertEqual(primeira_rodada.variacao, -1.56)
            self.assertEqual(primeira_rodada.media, 1.1)

    def test_time_logado(self):
        # Arrange and Act
        with requests_mock.mock() as m:
            url = '{api_url}/auth/time'.format(api_url=self.api_url)
            m.get(url, text=self.TIME_LOGADO)
            time = self.api.time_logado()
            primeiro_atleta = time.atletas[0]

            # Assert
            self.assertIsInstance(time, Time)
            self.assertEqual(time.patrimonio, 144.74)
            self.assertEqual(time.valor_time, 143.84961)
            self.assertEqual(time.ultima_pontuacao, 70.02978515625)
            self.assertIsInstance(time.atletas, list)
            self.assertIsInstance(primeiro_atleta, Atleta)
            self.assertEqual(primeiro_atleta.id, 38140)
            self.assertEqual(primeiro_atleta.apelido, 'Fernando Prass')
            self.assertEqual(primeiro_atleta.pontos, 7.5)
            self.assertEqual(primeiro_atleta.scout, {'DD': 5, 'FS': 1, 'GS': 1, 'PE': 1, 'SG': 1})
            self.assertEqual(primeiro_atleta.posicao, _posicoes[1])
            self.assertIsInstance(primeiro_atleta.clube, Clube)
            self.assertEqual(primeiro_atleta.clube.id, 275)
            self.assertEqual(primeiro_atleta.clube.nome, 'Palmeiras')
            self.assertEqual(primeiro_atleta.clube.abreviacao, 'PAL')
            self.assertEqual(primeiro_atleta.status, _atleta_status[7])
            self.assertIsInstance(time.info, TimeInfo)
            self.assertEqual(time.info.id, 471815)
            self.assertEqual(time.info.nome, 'Falydos FC')
            self.assertEqual(time.info.nome_cartola, 'Vicente Neto')
            self.assertEqual(time.info.slug, 'falydos-fc')
            self.assertTrue(time.info.assinante)


class ApiTest(unittest.TestCase):
    with open('testdata/clubes.json', 'rb') as f:
        CLUBES = f.read().decode('utf8')
    with open('testdata/ligas.json', 'rb') as f:
        LIGAS = f.read().decode('utf8')
    with open('testdata/ligas_patrocinadores.json', 'rb') as f:
        LIGAS_PATROCINADORES = f.read().decode('utf8')
    with open('testdata/mercado_atletas.json', 'rb') as f:
        MERCADO_ATLETAS = f.read().decode('utf8')
    with open('testdata/mercado_status_aberto.json', 'rb') as f:
        MERCADO_STATUS_ABERTO = f.read().decode('utf8')
    with open('testdata/times.json', 'rb') as f:
        TIMES = f.read().decode('utf-8')

    def setUp(self):
        self.api = cartolafc.Api()
        self.api_url = self.api._api_url

    def test_amigos_sem_autenticacao(self):
        # Act and Assert
        with self.assertRaisesRegexp(cartolafc.CartolaFCError, 'Esta função requer autenticação'):
            self.api.amigos()

    def test_clubes(self):
        # Arrange and Act
        with requests_mock.mock() as m:
            url = '{api_url}/clubes'.format(api_url=self.api_url)
            m.get(url, text=self.CLUBES)
            clubes = self.api.clubes()
            clube_flamengo = clubes[262]

            # Assert
            self.assertIsInstance(clubes, dict)
            self.assertIsInstance(clube_flamengo, Clube)
            self.assertEqual(clube_flamengo.id, 262)
            self.assertEqual(clube_flamengo.nome, 'Flamengo')
            self.assertEqual(clube_flamengo.abreviacao, 'FLA')

    def test_ligas(self):
        # Arrange and Act
        with requests_mock.mock() as m:
            url = '{api_url}/ligas'.format(api_url=self.api_url)
            m.get(url, text=self.LIGAS)
            ligas = self.api.ligas(query='premiere')
            primeira_liga = ligas[0]

            # Assert
            self.assertIsInstance(ligas, list)
            self.assertIsInstance(primeira_liga, Liga)
            self.assertEqual(primeira_liga.id, 36741)
            self.assertEqual(primeira_liga.nome, 'PREMIERE_LIGA_ENTEL')
            self.assertEqual(primeira_liga.slug, 'premiere-liga-entel')
            self.assertEqual(primeira_liga.descricao, u'“Vale tudo, só não vale...”')
            self.assertIsNone(primeira_liga.times)

    def test_mercado(self):
        # Arrange and Act
        with requests_mock.mock() as m:
            url = '{api_url}/mercado/status'.format(api_url=self.api_url)
            m.get(url, text=self.MERCADO_STATUS_ABERTO)
            status = self.api.mercado()

            # Assert
            self.assertIsInstance(status, Mercado)
            self.assertEqual(status.rodada_atual, 3)
            self.assertEqual(status.status.id, MERCADO_ABERTO)
            self.assertEqual(status.times_escalados, 3601523)
            self.assertIsInstance(status.fechamento, datetime)
            self.assertEqual(status.fechamento, datetime.fromtimestamp(1495904400))
            self.assertEqual(status.aviso, '')

    def test_mercado_atletas(self):
        # Arrange and Act
        with requests_mock.mock() as m:
            url = '{api_url}/atletas/mercado'.format(api_url=self.api_url)
            m.get(url, text=self.MERCADO_ATLETAS)
            mercado = self.api.mercado_atletas()
            primeiro_atleta = mercado[0]

            # Assert
            self.assertIsInstance(mercado, list)
            self.assertIsInstance(primeiro_atleta, Atleta)
            self.assertEqual(primeiro_atleta.id, 86935)
            self.assertEqual(primeiro_atleta.apelido, 'Rodrigo')
            self.assertEqual(primeiro_atleta.pontos, 0)
            self.assertEqual(primeiro_atleta.scout, {'CA': 1, 'FC': 3, 'FS': 1, 'PE': 2, 'RB': 2})
            self.assertEqual(primeiro_atleta.posicao, _posicoes[4])
            self.assertIsInstance(primeiro_atleta.clube, Clube)
            self.assertEqual(primeiro_atleta.clube.id, 292)
            self.assertEqual(primeiro_atleta.clube.nome, 'Sport')
            self.assertEqual(primeiro_atleta.clube.abreviacao, 'SPO')
            self.assertEqual(primeiro_atleta.status, _atleta_status[6])

    def test_parciais_mercado_fechado(self):
        # Arrange
        with requests_mock.mock() as m:
            url = '{api_url}/mercado/status'.format(api_url=self.api_url)
            m.get(url, text=self.MERCADO_STATUS_ABERTO)

            # Act and Assert
            with self.assertRaisesRegexp(cartolafc.CartolaFCError,
                                         'As pontuações parciais só ficam disponíveis com o mercado fechado.'):
                self.api.parciais()

    def test_patrocinadores(self):
        # Arrange and Act
        with requests_mock.mock() as m:
            url = '{api_url}/patrocinadores'.format(api_url=self.api_url)
            m.get(url, text=self.LIGAS_PATROCINADORES)
            ligas = self.api.ligas_patrocinadores()
            liga_brahma = ligas[62]

            # Assert
            self.assertIsInstance(ligas, dict)
            self.assertIsInstance(liga_brahma, LigaPatrocinador)
            self.assertEqual(liga_brahma.id, 62)
            self.assertEqual(liga_brahma.nome, 'Cerveja Brahma')
            self.assertEqual(liga_brahma.url_link, 'http://brahma.com.br')

    def test_pos_rodada_destaques(self):
        pass

    def test_times(self):
        # Arrange and Act
        with requests_mock.mock() as m:
            url = '{api_url}/times'.format(api_url=self.api_url)
            m.get(url, text=self.TIMES)
            times = self.api.times(query='Faly')
            primeiro_time = times[0]

            # Assert
            self.assertIsInstance(times, list)
            self.assertIsInstance(primeiro_time, TimeInfo)
            self.assertEqual(primeiro_time.id, 4626963)
            self.assertEqual(primeiro_time.nome, 'Falysson29')
            self.assertEqual(primeiro_time.nome_cartola, 'Alysson')
            self.assertEqual(primeiro_time.slug, 'falysson29')
            self.assertFalse(primeiro_time.assinante)

    def test_servidores_sobrecarregados(self):
        # Arrange
        with requests_mock.mock() as m:
            url = '{api_url}/mercado/status'.format(api_url=self.api_url)
            m.get(url)

            # Act and Assert
            with self.assertRaises(cartolafc.CartolaFCOverloadError):
                self.api.mercado()

# -*- encoding: utf-8 -*-
###############################################################################
#                                                                             #
# Copyright (C) 2015 TrustCode - www.trustcode.com.br                         #
#              Danimar Ribeiro <danimaribeiro@gmail.com>                      #
#                                                                             #
# This program is free software: you can redistribute it and/or modify        #
# it under the terms of the GNU Affero General Public License as published by #
# the Free Software Foundation, either version 3 of the License, or           #
# (at your option) any later version.                                         #
#                                                                             #
# This program is distributed in the hope that it will be useful,             #
# but WITHOUT ANY WARRANTY; without even the implied warranty of              #
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the               #
# GNU General Public License for more details.                                #
#                                                                             #
# You should have received a copy of the GNU General Public License           #
# along with this program.  If not, see <http://www.gnu.org/licenses/>.       #
#                                                                             #
###############################################################################

from openerp import models, fields, api
from openerp.exceptions import Warning
from openerp.service.db import dump_db
from boto.s3.connection import S3Connection
from boto.s3.key import Key
import socket
import os
import time
import zipfile
import oerplib
import logging
from datetime import datetime, timedelta

_logger = logging.getLogger(__name__)


def execute(connector, method, *args):
    res = False
    try:
        res = getattr(connector, method)(*args)
    except socket.error as e:
        raise e
    return res


class BackupExecuted(models.Model):
    _name = 'backup.executed'
    _order = 'backup_date'

    def _generate_s3_link(self):
        return self.s3_id

    name = fields.Char('Arquivo', size=100)
    configuration_id = fields.Many2one('trust.backup', string="Configuração")
    backup_date = fields.Datetime(string="Data")
    local_path = fields.Char(string="Caminho Local", readonly=True)
    s3_id = fields.Char(string="S3 Id", readonly=True)
    s3_url = fields.Char("Link S3", compute='_generate_s3_link', readonly=True)
    state = fields.Selection(
        string="Estado", default='not_started',
        selection=[('not_started', 'Não iniciado'),
                   ('executing', 'Executando'),
                   ('sending', 'Enviando'),
                   ('error', 'Erro'), ('concluded', 'Concluído')])


class TrustBackup(models.Model):
    _name = 'trust.backup'

    @api.multi
    @api.depends('interval', 'database_name')
    def name_get(self):
        result = []
        for backup in self:
            result.append(
                (backup.id,
                 backup.database_name +
                 " - " +
                 backup.interval))
        return result

    def _get_total_backups(self):
        for item in self:
            item.backup_count = self.env['backup.executed'].search_count(
                [('configuration_id', '=', item.id)])

    host = fields.Char(string="Endereço", size=200, default='localhost')
    port = fields.Char(string="Porta", size=10, default='8069')
    database_name = fields.Char(string='Banco de dados', size=100)
    interval = fields.Selection(
        string=u"Período",
        selection=[('hora', '1 hora'), ('seis', '6 horas'),
                   ('doze', '12 horas'), ('diario', u'Diário')])

    send_to_s3 = fields.Boolean('Enviar Amazon S3 ?')
    aws_access_key = fields.Char(string="Chave API S3", size=100)
    aws_secret_key = fields.Char(string="Chave Secreta API S3", size=100)
    backup_dir = fields.Char(string=u"Diretório", size=300)

    next_backup = fields.Datetime(string=u"Próximo Backup")
    backup_count = fields.Integer(
        string=u"Nº Backups",
        compute='_get_total_backups')

    _defaults = {
        'backup_dir': '/opt/backups/database/',
        'host': lambda *a: 'localhost',
        'port': lambda *a: '8069'
    }

    def _set_next_backup(self):
        if self.interval == 'hora':
            self.next_backup = datetime.now() + timedelta(hours=1)
        elif self.interval == 'seis':
            self.next_backup = datetime.now() + timedelta(hours=6)
        elif self.interval == 'seis':
            self.next_backup = datetime.now() + timedelta(hours=12)
        else:
            self.next_backup = datetime.now() + timedelta(days=1)

    @api.multi
    def execute_backup(self):
        try:
            self.write({'next_backup': datetime.now()})
            self.schedule_backup()
        except Exception as e:
            _logger.error(str(e).decode('utf-8', 'ignore'), exc_info=True)
            raise Warning(str(e))
            

    @api.model
    def schedule_backup(self):
        confs = self.search([])
        for rec in confs:

            if rec.next_backup:
                next_backup = datetime.strptime(
                    rec.next_backup,
                    '%Y-%m-%d %H:%M:%S')
            else:
                next_backup = datetime.now()
            if next_backup < datetime.now():

                oerp = oerplib.OERP(
                    rec.host,
                    protocol='xmlrpc',
                    port=rec.port,
                    timeout=1200)

                db_list = oerp.db.list()
                database_name = rec.database_name
                if database_name in db_list:
                    try:
                        if not os.path.isdir(rec.backup_dir):
                            os.makedirs(rec.backup_dir)
                    except:
                        raise
                    bkp_file = '%s_%s.sql' % (
                        database_name, time.strftime('%Y%m%d_%H_%M_%S'))
                    zip_file = '%s_%s.zip' % (
                        database_name, time.strftime('%Y%m%d_%H_%M_%S'))
                    file_path = os.path.join(rec.backup_dir, bkp_file)
                    zip_path = os.path.join(rec.backup_dir, zip_file)
                    fp = open(file_path, 'wb')
                    try:
                        dump_db(database_name, fp, backup_format='zip')
                    except Exception as ex:
                        _logger.error(str(ex).decode('utf-8', 'ignore'),
                                      exc_info=True)
                        continue

                    fp.close()
                    with zipfile.ZipFile(zip_path, 'w') as zipped:
                        zipped.write(file_path)
                    zipped.close()
                    os.remove(file_path)

                    backup_env = self.env['backup.executed']

                    if rec.send_to_s3:
                        key = rec.send_for_amazon_s3(zip_path, zip_file)
                        if not key:
                            key = 'Erro ao enviar para o Amazon S3'
                        backup_env.create({'backup_date': datetime.now(),
                                           'configuration_id': rec.id,
                                           's3_id': key, 'name': zip_file,
                                           'state': 'concluded',
                                           'local_path': zip_path})
                    else:
                        backup_env.create(
                            {'backup_date': datetime.now(), 'name': zip_file,
                             'configuration_id': rec.id, 'state': 'concluded',
                             'local_path': zip_path})
                    rec._set_next_backup()
            else:
                pass

    def send_for_amazon_s3(self, file_to_send, name_to_store):
        try:
            if self.aws_access_key and self.aws_secret_key:
                access_key = self.aws_access_key
                secret_key = self.aws_secret_key

                conexao = S3Connection(access_key, secret_key)
                bucket = conexao.create_bucket('backups_pelican')

                k = Key(bucket)
                k.key = name_to_store
                k.set_contents_from_filename(file_to_send)
            else:
                _logger.error(
                    u'Configurações do Amazon S3 não setadas, \
                    pulando armazenamento de backup')
        except Exception as ex:
            _logger.error(str(ex).decode('utf-8', 'ignore'), exc_info=True)

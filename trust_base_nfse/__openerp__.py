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


{
    'name': 'NFS-e Base',
    'summary': """Módulo que implementa o padrão base Abrasf -
                Esse módulo não é utilizavel sózinho, necessário implementar
                os métodos e o layout do municipio correspondente.
                Depends: suds, suds_requests""",
    'version': '8.0',
    'category': 'Localisation',
    'author': 'Trustcode',
    'license': 'AGPL-3',
    'website': 'http://www.trustcode.com.br',
    'contributors': ['Danimar Ribeiro <danimaribeiro@gmail.com>',
                     'Mackilem Van der Laan Soares <mack.vdl@gmail.com>'
                     ],
    'depends': [
        'account', 'l10n_br_base', 
        'l10n_br_account_service', 
        'l10n_br_account_product'
    ],
    'data': [
        'data/trust_base_nfse_data.xml',
        'views/base_nfse_view.xml',
        'views/account_invoice_view.xml',
        'views/res_company_view.xml',
        'workflow/account_invoice_workflow.xml'
    ],
    'instalable': True
}

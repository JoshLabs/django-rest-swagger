import logging
import urlparse
from django.core.files.base import ContentFile
from django.core.files.storage import get_storage_class
from django.core.management import BaseCommand

from rest_framework.renderers import JSONRenderer
import rest_framework_swagger as rfs
from rest_framework_swagger.docgenerator import DocumentationGenerator
from rest_framework_swagger.urlparser import UrlParser


logger = logging.getLogger(__name__)


class Command(BaseCommand):
    def handle(self, *args, **options):
        assert rfs.SWAGGER_SETTINGS.get(u'ENABLE_OFFLINE_DOCS', False), u'Swagger setting ENABLE_OFFLINE_DOCS must be set to generate offline docs'
        logger.info(u'Dropping previous docs')
        storage_class = rfs.SWAGGER_SETTINGS.get(u'DEFAULT_DOCS_STORAGE', u'')
        assert storage_class, u'Swagger setting DEFAULT_DOCS_STORAGE must be set to generate offline docs'
        storage = get_storage_class(storage_class)(**rfs.SWAGGER_SETTINGS.get(u'FILE_STORAGE_KWARGS', {}))
        if storage.exists(u'docs'):
            dirs, files = storage.listdir(u'docs')
            for filename in files:
                logger.info(u'Dropping {}'.format(filename))
                storage.delete(u'docs/{}'.format(filename))

        logger.info(u'Generating base.json')
        apps = get_apps()
        renderer = JSONRenderer()
        storage.save(u'docs/base.json', ContentFile(renderer.render(apps)))
        for app in apps[u'apis']:
            path = urlparse.urlparse(app[u'path']).path
            path = path.lstrip(u'/')
            logger.info(u'Processing path: {}'.format(path))
            storage.save(u'docs/{}.json'.format(path.replace(u'/', u'_')), ContentFile(renderer.render(generate_offline_docs(path))))


def get_apps():
    """
    Function to generate Resource listing for swagger
    :return dict: Data to be written to file
    """
    url_parser = UrlParser()
    exclude_namespaces = rfs.SWAGGER_SETTINGS.get(u'exclude_namespaces')
    resources = url_parser.get_top_level_apis(url_parser.get_apis(exclude_namespaces=exclude_namespaces))
    return {
            u'apiVersion': rfs.SWAGGER_SETTINGS.get(u'api_version', u''),
            u'swaggerVersion': u'1.2',
            u'basePath': rfs.SWAGGER_SETTINGS.get(u'offline_base_path', u''),
            u'apis': [{u'path': u'/{}'.format(path)} for path in resources],
            u'info': rfs.SWAGGER_SETTINGS.get(u'info', {
                u'contact': u'',
                u'description': u'',
                u'license': u'',
                u'licenseUrl': u'',
                u'termsOfServiceUrl': u'',
                u'title': u'',
            }),
        }


def generate_offline_docs(path=u''):
    """
    Function to generate API listing for swagger
    :param path(string): Path for which docs to be generated
    :return dict: Data to be written to file
    """
    api_list = UrlParser().get_apis(filter_path=path)
    doc_generator = DocumentationGenerator()
    url = urlparse.urlparse(rfs.SWAGGER_SETTINGS.get(u'offline_base_path', u''))
    return {
            u'apiVersion': rfs.SWAGGER_SETTINGS.get(u'api_version', u''),
            u'swaggerVersion': u'1.2',
            u'basePath': u'{}://{}:{}'.format(url.scheme, url.hostname, url.port),
            u'resourcePath': path,
            u'apis': doc_generator.generate(api_list),
            u'models': doc_generator.get_models(api_list),
        }

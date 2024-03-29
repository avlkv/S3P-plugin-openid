"""
Нагрузка плагина SPP

1/2 документ плагина
"""
import logging
import time
import dateparser
from datetime import datetime
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.webdriver import WebDriver
from src.spp.types import SPP_document
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


class OPENID:
    """
    Класс парсера плагина SPP

    :warning Все необходимое для работы парсера должно находится внутри этого класса

    :_content_document: Это список объектов документа. При старте класса этот список должен обнулиться,
                        а затем по мере обработки источника - заполняться.


    """

    SOURCE_NAME = 'openid'
    _content_document: list[SPP_document]

    HOST = 'https://openid.net/specs/?C=M;O=D'
    def __init__(self, webdriver: WebDriver, last_document: SPP_document = None, max_count_documents: int = 100,
                 *args, **kwargs):
        """
        Конструктор класса парсера

        По умолчанию внего ничего не передается, но если требуется (например: driver селениума), то нужно будет
        заполнить конфигурацию
        """
        # Обнуление списка
        self._content_document = []

        self.driver = webdriver
        self.wait = WebDriverWait(self.driver, timeout=20)
        self.max_count_documents = max_count_documents
        self.last_document = last_document

        # Логер должен подключаться так. Вся настройка лежит на платформе
        self.logger = logging.getLogger(self.__class__.__name__)
        self.logger.debug(f"Parser class init completed")
        self.logger.info(f"Set source: {self.SOURCE_NAME}")
        ...

    def content(self) -> list[SPP_document]:
        """
        Главный метод парсера. Его будет вызывать платформа. Он вызывает метод _parse и возвращает список документов
        :return:
        :rtype:
        """
        self.logger.debug("Parse process start")
        try:
            self._parse()
        except Exception as e:
            self.logger.debug(f'Parsing stopped with error: {e}')
        else:
            self.logger.debug("Parse process finished")
        return self._content_document

    def _parse(self):
        """
        Метод, занимающийся парсингом. Он добавляет в _content_document документы, которые получилось обработать
        :return:
        :rtype:
        """
        # HOST - это главная ссылка на источник, по которому будет "бегать" парсер
        self.logger.debug(F"Parser enter to {self.HOST}")

        # ========================================
        # Тут должен находится блок кода, отвечающий за парсинг конкретного источника
        # -
        self.driver.get(self.HOST)

        specs = self.driver.find_elements(By.XPATH, '//a[contains(text(),\'.html\')]')
        web_links = [spec.get_attribute('href') for spec in specs]
        for web_link in web_links:
            self.driver.get(web_link)
            if len(self.driver.find_elements(By.XPATH, '//h2[text() = \'Renamed Specification\']')) > 0:
                self.logger.debug('Waiting redirect')
                time.sleep(7)
            time.sleep(2)

            try:
                title = self.driver.find_element(By.ID, 'title').text
            except:
                title = self.driver.find_element(By.TAG_NAME, 'h1').text

            try:
                pub_date = dateparser.parse(self.driver.find_element(By.TAG_NAME, 'time').text)
            except:
                pub_date = dateparser.parse(self.driver.find_elements(By.XPATH, '//table[not(@class = \'TOCbug\')][1]/tbody/tr/td')[-1].text)

            try:
                abstract = self.driver.find_element(By.ID, 'section-abstract').text
            except:
                abstract = None

            text_content = self.driver.find_element(By.TAG_NAME, 'body').text

            try:
                workgroup = self.driver.find_element(By.CLASS_NAME, 'workgroup').text
            except:
                workgroup = None

            try:
                authors = []
                author_struct = self.driver.find_elements(By.CLASS_NAME, 'author')
                for author in author_struct:
                    authors.append({'name': author.find_element(By.CLASS_NAME, 'author-name').text,
                                    'org': author.find_element(By.CLASS_NAME, 'org').text})
            except:
                authors = [x.text for x in self.driver.find_elements(By.XPATH, '//table[not(@class = \'TOCbug\')][1]/tbody/tr/td')]

            other_data = {'workgroup': workgroup,
                          'authors': authors}

            doc = SPP_document(None,
                               title,
                               abstract,
                               text_content,
                               web_link,
                               None,
                               other_data,
                               pub_date,
                               datetime.now())

            self.find_document(doc)

        # ---
        # ========================================
        ...

    def _find_document_text_for_logger(self, doc: SPP_document):
        """
        Единый для всех парсеров метод, который подготовит на основе SPP_document строку для логера
        :param doc: Документ, полученный парсером во время своей работы
        :type doc:
        :return: Строка для логера на основе документа
        :rtype:
        """
        return f"Find document | name: {doc.title} | link to web: {doc.web_link} | publication date: {doc.pub_date}"

    def find_document(self, _doc: SPP_document):
        """
        Метод для обработки найденного документа источника
        """
        if self.last_document and self.last_document.hash == _doc.hash:
            raise Exception(f"Find already existing document ({self.last_document})")

        if self.max_count_documents and len(self._content_document) >= self.max_count_documents:
            raise Exception(f"Max count articles reached ({self.max_count_documents})")

        self._content_document.append(_doc)
        self.logger.info(self._find_document_text_for_logger(_doc))
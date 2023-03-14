#!/usr/bin/env python3

import json
import requests
import parsel

import prettyprinter

import fake_useragent

from retry import retry

prettyprinter.install_extras()

# Aca se asignan variables esenciales como el link del sitio web
# (sin el atributo page en la URL, el cual marca el número de páginas)
# y el total de páginas actualizado.
LAWS_URL: str = "https://parlamento.gub.uy/documentosyleyes/leyes?Ly_Nro=&Fechadesde=1798-01-15&Fechahasta=2023-03-02&Ltemas&Tipobusqueda=T&Searchtext=&page="

URL_WEB_ZERO: str = "https://parlamento.gub.uy/documentosyleyes/leyes?Ly_Nro=&Fechadesde=1798-01-15&Fechahasta=2023-03-02&Ltemas&Tipobusqueda=T&Searchtext=&page=0"

BASE_URL: str = "https://www.impo.com.uy/"

ua = fake_useragent.UserAgent()

CHROME_USER_AGENT: str = ua.chrome

HEADERS: dict[str, str] = {"User-Agent": CHROME_USER_AGENT}


def get_last_page_number() -> int:
    """ Get the number of the last page that contain laws. """
    resp_str: str = requests.get(
        URL_WEB_ZERO, headers=HEADERS).text
    parsel_selector = parsel.Selector(resp_str)
    last_page_button = parsel_selector.xpath(
        './/a[@class="page-link" and @title="Ir a la última página"]'
    )[0]
    href: str = last_page_button.attrib["href"]
    page_index: int = int(href[-3:])

    return page_index


def get_urls_in_page_index(page_index: int) -> list[str]:
    urls_in_page_index: list[str] = []
    current_website_url: str = f"{LAWS_URL}{page_index}"

    resp_str: str = requests.get(
        current_website_url, headers=HEADERS).text
    parsel_selector = parsel.Selector(resp_str)

    table_elements: parsel.selector.SelectorList = parsel_selector.xpath(
        './/td[@class="views-field views-field-Ly-file-1"]/a'
    )

    for row in table_elements:
        href: str = row.attrib["href"]
        urls_in_page_index.append(href)

    return urls_in_page_index


def get_law_id(law_url: str) -> str:
    law_id: str = law_url.split("/")[5]
    return law_id


def get_section_number(section_url: str) -> str:
    section_number: str = section_url.split("/")[-1]
    return section_number


def get_section_url(section_selector_obj) -> str:
    section_path: str = section_selector_obj.attrib["href"]
    section_url: str = f"{BASE_URL.rstrip('/')}{section_path}"

    return section_url



class IMPOScraper:
    def __init__(self):
        self.LAWS_CONTENT_DICT = {}

    #########################
    #   SCRAPER FUNCTIONS   #
    #########################
    def save_to_json(self) -> None:
        """ Save the laws data to a JSON file. """
        with open("impodata.json", "w", encoding="utf-8") as f:
            json.dump(
                self.LAWS_CONTENT_DICT,
                f,
                indent=4,
                ensure_ascii=False
            )

        return None

    def scrape_laws_content(self, law_url: str):
        print("#" * 60)
        print(f"LAW URL: {law_url}")
        try:
            law_website_code: str = requests.get(
                law_url, headers=HEADERS).text
            parsel_selector = parsel.Selector(law_website_code)

            law_title: str = parsel_selector.xpath(
                ".//h2//text()"
            )[0].get().rstrip("\r\n")
            print(f"LAW TITLE: {law_title}")

            law_id: str = get_law_id(law_url=law_url)
            print(f"LAW ID: {law_id}")

            law_sections_objs: parsel.selector.SelectorList = parsel_selector.xpath(
                ".//h4/a"
            )

            for section_selector_obj in law_sections_objs:
                section_url = get_section_url(
                    section_selector_obj=section_selector_obj)
                self.scrape_section_content(
                    section_url=section_url,
                    law_id=law_id,
                    law_title=law_title
                )
        except Exception as e:
            print("Artículo inválido.")

    def scrape_section_content(self, section_url: str, law_id: str, law_title: str):
        print("*" * 50)
        section_number: str = get_section_number(
            section_url=section_url)

        section_website_code: str = requests.get(
            section_url, headers=HEADERS).text
        parsel_selector = parsel.Selector(section_website_code)

        section_title_sel = parsel_selector.xpath(
            ".//h4[@class='resultado']/text()")
        section_title: str = section_title_sel.get()
        print(f"Section title: {section_title}")

        section_content_sel = parsel_selector.xpath(
            ".//pre//text()")

        section_content_text_list: list[str] = section_content_sel.getall()
        section_content_text_list = [
            text.strip("\r\n").replace(
                "\r\n", "\n").strip(" ") for text in section_content_text_list
        ]
        section_content_text = "\n".join(section_content_text_list)

        print("Section content:")
        print(section_content_text)

        if law_id not in self.LAWS_CONTENT_DICT.keys():
            self.LAWS_CONTENT_DICT[law_id] = {"law_title": law_title}

        self.LAWS_CONTENT_DICT[law_id][section_title] = section_content_text

    ######################
    #   EXECUTION FLOW   #
    ######################
    def scrape(self):
        self.last_page_number: int = get_last_page_number()

        self.actual_page_index: int = 0

        while self.actual_page_index <= self.last_page_number:
            self.scrape_impo_page(page_index=self.actual_page_index)
            self.actual_page_index += 1

    @retry(tries=10)
    def scrape_impo_page(self, page_index: int):
        print("-" * 60)
        print(f"PAGE INDEX: {page_index}")
        print("-" * 60)
        urls_in_page_index: list[str] = get_urls_in_page_index(
            page_index=page_index
        )

        for law_url in urls_in_page_index:
            self.scrape_laws_content(law_url=law_url)


if __name__ == "__main__":
    impo_scraper = IMPOScraper()
    impo_scraper.scrape()
    impo_scraper.save_to_json()

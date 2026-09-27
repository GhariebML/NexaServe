from scraper.scraper import DEPIDataScraper


def main() -> None:
    scraper = DEPIDataScraper()
    dataset = scraper.save_outputs()
    print(f"Scraped {len(dataset['pages'])} pages, {len(dataset['faqs'])} FAQs, {len(dataset['documents'])} documents.")


if __name__ == '__main__':
    main()

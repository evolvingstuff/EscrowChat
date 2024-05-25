from scrape import scrape_and_parse_data


def main():
    try:
        scrape_and_parse_data()
    except Exception as e:
        print(e)
        # TODO: further error handling
        return


if __name__ == '__main__':
    main()

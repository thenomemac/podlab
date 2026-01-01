def main():
    import fire
    from .app import app

    fire.Fire({func.__name__: func for func in [app]})


if __name__ == "__main__":
    main()

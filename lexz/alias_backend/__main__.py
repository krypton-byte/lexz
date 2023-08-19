from .backend import backends


def show_backend():
    print('List of Backend')
    for backend in backends:
        print(f'- name: {backend.name}\n  description: {backend.desc}')


if __name__ == '__main__':
    show_backend()

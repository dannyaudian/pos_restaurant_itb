from setuptools import setup, find_packages

setup(
    name='restaurant_pos_core',
    version='1.0.0',
    description='Core POS module for restaurant operations',
    author='PT. Innovasi Terbaik Bangsa',
    packages=find_packages(),
    include_package_data=True,
    zip_safe=False,
    install_requires=['frappe']
)

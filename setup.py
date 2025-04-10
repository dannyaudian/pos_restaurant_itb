from setuptools import setup, find_packages

setup(
    name="pos_restaurant_itb",
    version="0.1.0",
    description="Restaurant POS Module for ERPNext",
    author="PT. Innovasi Terbaik Bangsa",
    author_email="info@inovasiterbaik.co.id",
    packages=find_packages(),
    zip_safe=False,
    include_package_data=True,
    install_requires=["frappe"],
)
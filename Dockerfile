FROM python:3.10 AS build

COPY . /code
WORKDIR /code

RUN apt update && apt install -y libxres-dev

RUN pip install -r requirements.txt && pip install pyinstaller

RUN pyinstaller --onefile pherguson.py

FROM scratch AS binaries

COPY --from=build /code/dist/pherguson /

CMD ["/pherguson"]

# Guía de Contribución — TMAC

¡Gracias por tu interés en contribuir a TMAC! Esta guía cubre cómo configurar el entorno,
ejecutar los tests, y el proceso para añadir nuevas reglas de amenazas.

## Tabla de contenidos

1. [Configurar el entorno de desarrollo](#1-configurar-el-entorno-de-desarrollo)
2. [Ejecutar los tests](#2-ejecutar-los-tests)
3. [Contribuir nuevas reglas](#3-contribuir-nuevas-reglas)
4. [Proceso de Pull Request](#4-proceso-de-pull-request)

---

## 1. Configurar el entorno de desarrollo

### Requisitos previos

- Python **3.10+**
- [Poetry](https://python-poetry.org/docs/#installation) (gestor de dependencias)
- Git

### Pasos

```bash
# 1. Clonar el repositorio
git clone https://github.com/tmac-security/tmac.git
cd tmac

# 2. Instalar dependencias (incluyendo dev)
poetry install

# 3. Activar el entorno virtual de Poetry
poetry shell

# 4. Verificar la instalación
tmac --version
```

### Alternativa con pip

```bash
python -m venv venv
source venv/bin/activate  # Windows: .\venv\Scripts\Activate.ps1
pip install --require-hashes -r requirements-dev.txt   # versiones fijadas, auditadas y verificadas por hash
pip install -e . --no-deps
```

### Dependencias y lockfiles

- `requirements.in` / `requirements-dev.in`: dependencias directas con rangos (se editan a mano).
- `requirements.txt` / `requirements-dev.txt`: lockfiles **generados** con versión exacta y hash SHA-256 de cada paquete. No se editan a mano.

Para agregar o actualizar una dependencia, edita el `.in`, regenera los lockfiles con [uv](https://docs.astral.sh/uv/) y audítalos:

```bash
uv pip compile requirements.in --universal --generate-hashes --python-version 3.10 -o requirements.txt
uv pip compile requirements-dev.in --universal --generate-hashes --python-version 3.11 -o requirements-dev.txt
pip-audit --require-hashes --disable-pip -r requirements.txt
pip-audit --require-hashes --disable-pip -r requirements-dev.txt
```

Para subir versiones dentro de los rangos, agrega `--upgrade` (o `--upgrade-package <nombre>`) al comando de `uv pip compile`. El CI vuelve a auditar los lockfiles cada semana.

### Herramientas de desarrollo incluidas

| Herramienta | Uso |
| :--- | :--- |
| `pytest` | Ejecución de tests |
| `pytest-cov` | Cobertura de código |
| `hypothesis` | Property-based testing |
| `ruff` | Linting y formato |
| `black` | Formateo de código |
| `mypy` | Verificación de tipos |

---

## 2. Ejecutar los tests

### Suite completa

```bash
pytest
```

### Con cobertura de código

```bash
# Cobertura del código de producción (objetivo: ≥90%)
pytest --cov=tmac --cov-report=term-missing

# Solo tests de integración (objetivo: ≥80%)
pytest tests/integration/ --cov=tmac
```

### Tests específicos

```bash
# Solo tests unitarios
pytest tests/unit/

# Solo tests de integración
pytest tests/integration/

# Un módulo específico
pytest tests/unit/test_evaluator.py

# Un test específico
pytest tests/unit/test_evaluator.py::test_evaluator_list_any_match -v
```

### Tests de propiedades (Hypothesis)

Los tests de propiedades usan Hypothesis con `@settings(max_examples=100)`.
Para ejecutarlos con más ejemplos durante desarrollo:

```bash
# Ejecutar con más ejemplos para mayor confianza
pytest tests/ -k "property" --hypothesis-seed=0
```

### Linting y tipos

```bash
# Linting con ruff
ruff check src/ tests/

# Formateo con black
black src/ tests/

# Verificación de tipos con mypy
mypy src/tmac/
```

Los tres son obligatorios en el CI (job *Lint & types*): un PR no pasa si `ruff check src tests`, `black --check src tests` o `mypy src` reportan errores. Ruff y black usan líneas de 100 caracteres (`pyproject.toml`).

Los commits de solo formato se listan en `.git-blame-ignore-revs`; para que `git blame` los salte:

```bash
git config blame.ignoreRevsFile .git-blame-ignore-revs
```

---

## 3. Contribuir nuevas reglas

Las reglas de amenazas se definen en archivos `threats.yaml` dentro de `src/tmac/rules/`.

### Schema de una regla

```yaml
- id: TMAC-AWS-{SERVICE}-{NNN}       # Formato obligatorio, ej: TMAC-AWS-S3-007
  name: "Nombre descriptivo de la amenaza"
  resource_type: "aws_resource_type"  # Tipo de recurso Terraform exacto
  check:
    attribute: "path.al.atributo"     # Path al atributo del recurso
    condition: "equals"               # Ver operadores disponibles
    values: ["valor_esperado"]
    and_check:                        # Opcional: condición adicional (AND lógico)
      attribute: "otro.atributo"
      condition: "contains"
      values: ["otro_valor"]
  severity: "Critical"                # Critical | High | Medium | Low | Info
  stride: "Information Disclosure"    # Categoría STRIDE (ver lista abajo)
  description: >
    Descripción detallada de la amenaza y su impacto.
  mitigation: >
    Pasos concretos para mitigar la amenaza con ejemplo de código Terraform.
  references:
    - "https://docs.aws.amazon.com/..."
    - "CIS AWS Benchmark vX.X - X.X"
  tags: ["servicio", "categoria", "etiqueta"]
```

### Convenciones de nomenclatura

- **ID**: `TMAC-{CLOUD}-{SERVICE}-{NNN}` donde:
  - `CLOUD`: proveedor cloud en mayúsculas (`AWS`, `GCP`, `AZURE`)
  - `SERVICE`: servicio en mayúsculas (`S3`, `IAM`, `SG`, `RDS`, `EC2`, `VPC`, `CW`)
  - `NNN`: número secuencial de 3 dígitos (`001`, `002`, ...)
- **`resource_type`**: debe coincidir exactamente con el tipo de recurso Terraform (ej. `aws_s3_bucket`)
- **`severity`**: usar `Critical`, `High`, `Medium`, `Low`, o `Info` (con mayúscula inicial)
- **`stride`**: una de las 6 categorías: `Spoofing`, `Tampering`, `Repudiation`, `Information Disclosure`, `Denial of Service`, `Elevation of Privilege`

### Operadores de condición disponibles

| Operador | Descripción |
| :--- | :--- |
| `equals` | El atributo es igual al valor. |
| `not_equals` | El atributo no es igual al valor. |
| `in` | El atributo está en la lista de valores. |
| `not_in` | El atributo no está en la lista de valores. |
| `contains` | El atributo contiene el valor (string o lista). |
| `not_contains` | El atributo no contiene el valor. |
| `regex` | El atributo coincide con la expresión regular. |
| `exists` | El atributo existe en el recurso. |
| `not_exists` | El atributo no existe en el recurso. |

### Ejemplo completo: nueva regla S3

```yaml
- id: TMAC-AWS-S3-007
  name: "S3 Bucket sin Versionado Habilitado"
  resource_type: "aws_s3_bucket"
  check:
    attribute: "versioning.enabled"
    condition: "not_exists"
    values: []
  severity: "Medium"
  stride: "Tampering"
  description: >
    El bucket S3 no tiene habilitado el versionado de objetos. Sin versionado,
    la sobreescritura o eliminación accidental o maliciosa de objetos es
    irreversible, facilitando ataques de Tampering.
  mitigation: >
    Habilita el versionado en el bucket:
      resource "aws_s3_bucket_versioning" "example" {
        bucket = aws_s3_bucket.example.id
        versioning_configuration {
          status = "Enabled"
        }
      }
  references:
    - "https://docs.aws.amazon.com/AmazonS3/latest/userguide/Versioning.html"
  tags: ["s3", "versioning", "data-integrity"]
```

### Añadir fixtures de test para la nueva regla

Toda regla nueva debe incluir al menos un fixture positivo (que dispara la regla) y uno negativo (que no la dispara) en `tests/fixtures/`:

**`tests/fixtures/s3_no_versioning.tf`** (positivo — dispara la regla):
```hcl
resource "aws_s3_bucket" "no_versioning" {
  bucket = "my-bucket-no-versioning"
}
```

**`tests/fixtures/s3_with_versioning.tf`** (negativo — no dispara la regla):
```hcl
resource "aws_s3_bucket" "with_versioning" {
  bucket = "my-bucket-with-versioning"
}

resource "aws_s3_bucket_versioning" "example" {
  bucket = aws_s3_bucket.with_versioning.id
  versioning_configuration {
    status = "Enabled"
  }
}
```

Luego añade el par a `RULE_FIXTURES` en `tests/integration/test_rules.py`:

```python
RULE_FIXTURES = [
    # ... reglas existentes ...
    ("TMAC-AWS-S3-007", "s3_no_versioning.tf",    True),
    ("TMAC-AWS-S3-007", "s3_with_versioning.tf",  False),
]
```

---

## 4. Proceso de Pull Request

1. **Crea un branch** desde `main` con un nombre descriptivo:
   ```bash
   git checkout -b feat/tmac-aws-s3-007-versioning
   ```

2. **Implementa los cambios** siguiendo las convenciones del proyecto.

3. **Añade o actualiza tests** — toda nueva regla requiere fixtures y tests parametrizados.

4. **Verifica que los tests pasan**:
   ```bash
   pytest --cov=tmac
   ruff check src/ tests/
   mypy src/tmac/
   ```

5. **Actualiza `CHANGELOG.md`** añadiendo tu cambio bajo `[Unreleased]`.

6. **Abre el Pull Request** con una descripción clara de:
   - Qué amenaza detecta la nueva regla
   - Por qué es relevante (referencia a CIS Benchmark, CVE, etc.)
   - Cómo se probó

### Criterios de aceptación para nuevas reglas

- [ ] ID sigue el formato `TMAC-{CLOUD}-{SERVICE}-{NNN}`
- [ ] `resource_type` es un tipo de recurso Terraform válido
- [ ] `severity` y `stride` usan los valores permitidos
- [ ] Fixture positivo dispara exactamente un `Finding` con el `rule_id` correcto
- [ ] Fixture negativo no produce ningún `Finding`
- [ ] Tests pasan con `pytest` sin errores
- [ ] Cobertura de código no disminuye por debajo del 90%

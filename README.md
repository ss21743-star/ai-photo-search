# AI Photo Search – Cloud Computing Assignment 3

Photo album web app searchable in natural language (Lex + OpenSearch + Rekognition).

| Folder | Contents |
|---|---|
| `front-end/` | Static website (S3 bucket B1) + API Gateway generated JS SDK |
| `lambda-functions/` | `index-photos` (LF1) and `search-photos` (LF2) |
| `other-scripts/` | CloudFormation template (T1) and other scripts |

CI/CD: pushing to `main` triggers CodePipeline P1 (Lambdas) and P2 (frontend).

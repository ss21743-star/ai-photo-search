# Lambda functions

- index-photos (LF1): S3 PUT trigger, Rekognition labels + custom labels, indexes into OpenSearch "photos".
- search-photos (LF2): Lex keyword extraction, OpenSearch search, returns photo URLs and labels.

Deployed automatically by CodePipeline P1 on every push that changes this folder.
demo update for video

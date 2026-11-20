"""CodePipeline deploy step (used instead of CodeBuild, whose quota is 0 on this account).
UserParameters = "lambdas"  -> zips lambda-functions/<fn>/ and updates index-photos + search-photos (P1)
UserParameters = "frontend" -> copies front-end/* to the S3 website bucket B1 (P2)
"""
import io, mimetypes, os, zipfile
import boto3

s3 = boto3.client("s3")
lam = boto3.client("lambda")
cp = boto3.client("codepipeline")
FUNCTIONS = ["index-photos", "search-photos"]
B1 = os.environ["FRONTEND_BUCKET"]


def deploy_lambdas(src):
    for fn in FUNCTIONS:
        prefix = f"lambda-functions/{fn}/"
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
            for n in src.namelist():
                if n.startswith(prefix) and not n.endswith("/"):
                    z.writestr(n[len(prefix):], src.read(n))
        lam.update_function_code(FunctionName=fn, ZipFile=buf.getvalue())
        lam.get_waiter("function_updated").wait(FunctionName=fn)
        if lam.get_function_configuration(FunctionName=fn)["Handler"] != "lambda_function.lambda_handler":
            lam.update_function_configuration(FunctionName=fn, Handler="lambda_function.lambda_handler")
            lam.get_waiter("function_updated").wait(FunctionName=fn)
        print("deployed", fn)


def deploy_frontend(src):
    for n in src.namelist():
        if n.startswith("front-end/") and not n.endswith("/") and not n.endswith("buildspec.yml"):
            key = n[len("front-end/"):]
            ctype = mimetypes.guess_type(key)[0] or "application/octet-stream"
            s3.put_object(Bucket=B1, Key=key, Body=src.read(n), ContentType=ctype)
            print("uploaded", key)


def lambda_handler(event, context):
    job = event["CodePipeline.job"]
    try:
        loc = job["data"]["inputArtifacts"][0]["location"]["s3Location"]
        blob = s3.get_object(Bucket=loc["bucketName"], Key=loc["objectKey"])["Body"].read()
        src = zipfile.ZipFile(io.BytesIO(blob))
        mode = job["data"]["actionConfiguration"]["configuration"]["UserParameters"]
        deploy_lambdas(src) if mode == "lambdas" else deploy_frontend(src)
        cp.put_job_success_result(jobId=job["id"])
    except Exception as e:
        print("ERROR", repr(e))
        cp.put_job_failure_result(jobId=job["id"], failureDetails={"type": "JobFailed", "message": str(e)[:500]})

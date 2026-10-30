---
layout: layouts/page.html
---
# Security

Ensuring our platform remains secure is vital and protecting your information is our highest priority.

Digicoop SARL operates the [https://sqlify.me](https://sqlify.me) website.

Digicoop is ISO 27001 certified.

## Company security

Good security starts with the people. All our employees are trained to our security and data privacy protocols. Access rights are based on employee’s job function and role.

Sensitive secrets and information is never stored unencrypted. Access to servers is limited, strictly monitored and fully logged.

Two factor authentification is mandatory for all employee accounts for internal apps as well as third-party services.

## System security

Web connections to the SQLify service are via TLS 1.2 and above. We support forward secrecy and AES-GCM, and prohibit insecure connections using TLS 1.1 and below or RC4.

Penetration tests are automatically performed on a weekly basis. We follow OWASP best practives.

Sensitive data (like oauth tokens) are encrypted using AES256.

Access to customer data is only done if requested by the customer and logged.

## Data center security

SQLify is hosted by [Hetzner](http://ovh.com) in Germany.

[You can read more about security at Hetnzer on their Security page](https://www.hetzner.com/unternehmen/zertifizierung).

Files and backups are hosted in [AWS S3](https://aws.amazon.com/s3) at their Ireland data center. Amazon also provides state of the art security for all their data center. [Read more on their security page](https://docs.aws.amazon.com/AmazonS3/latest/dev/security.html).

## Backup & recovery

We perform daily backups of our database, encrypt them in place (AES256) and then store them in AWS S3.

Recovery procedures are tested every quarter.

## Privacy

See our [Privacy Policy](/privacy).

## Availability

We are committed to making SQLify consistently available to you and your teams. Our systems are constantly monitored to keep your work uninterrupted. You can always monitor our availability at our [status page](https://status.sqlify.me).

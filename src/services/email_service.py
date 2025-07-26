# src/services/email_service.py
import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
import logging
from typing import List, Dict, Optional, Any
from datetime import datetime
import jinja2
import os
from pathlib import Path

class EmailService:
    def __init__(self, config: dict):
        """
        Initialize Email Service

        Args:
            config: Configuration dictionary with email settings
        """
        self.config = config
        self.logger = logging.getLogger(__name__)

        # Email configuration
        self.smtp_server = config.get('smtp_server', 'smtp.gmail.com')
        self.smtp_port = config.get('smtp_port', 587)
        self.username = config.get('username')
        self.password = config.get('password')
        self.recipients = config.get('recipients', [])

        # Validate configuration
        if not self.username or not self.password:
            self.logger.error("Email username or password not configured")
            raise ValueError("Email credentials not provided")

        if not self.recipients:
            self.logger.warning("No email recipients configured")

        # Initialize Jinja2 template environment
        template_dir = Path(__file__).parent.parent / 'templates' / 'email'
        template_dir.mkdir(parents=True, exist_ok=True)

        self.jinja_env = jinja2.Environment(
            loader=jinja2.FileSystemLoader(str(template_dir)),
            autoescape=jinja2.select_autoescape(['html', 'xml'])
        )

        # Create default templates if they don't exist
        self._create_default_templates()

        self.logger.info(f"Email service initialized for {len(self.recipients)} recipients")

    def _create_default_templates(self):
        """Create default email templates if they don't exist"""
        template_dir = Path(__file__).parent.parent / 'templates' / 'email'

        # Daily summary template
        daily_summary_template = """
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="utf-8">
                <title>Daily Content Summary</title>
                <style>
                    body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
                    .header { background-color: #f4f4f4; padding: 20px; text-align: center; }
                    .content { padding: 20px; }
                    .summary-section { margin-bottom: 30px; }
                    .source-list { background-color: #f9f9f9; padding: 15px; border-left: 4px solid #007cba; }
                    .source-item { margin-bottom: 10px; }
                    .source-link { color: #007cba; text-decoration: none; }
                    .source-link:hover { text-decoration: underline; }
                    .stats { background-color: #e8f4f8; padding: 15px; border-radius: 5px; }
                    .footer { background-color: #f4f4f4; padding: 15px; text-align: center; font-size: 12px; color: #666; }
                </style>
            </head>
            <body>
                <div class="header">
                    <h1>🤖 AI Assistant Daily Summary</h1>
                    <p>{{ generated_date }}</p>
                </div>

                <div class="content">
                    <div class="stats">
                        <h3>📊 Summary Statistics</h3>
                        <ul>
                            <li><strong>New Content Items:</strong> {{ content_count }}</li>
                            <li><strong>Sources Monitored:</strong> {{ sources|length }}</li>
                            <li><strong>Generated At:</strong> {{ generated_at }}</li>
                        </ul>
                    </div>

                    {% if content_count > 0 %}
                    <div class="summary-section">
                        <h2>📝 Content Summary</h2>
                        <div>
                            {{ summary|safe }}
                        </div>
                    </div>

                    <div class="summary-section">
                        <h2>🔗 Sources</h2>
                        <div class="source-list">
                            {% for source in sources %}
                            <div class="source-item">
                                <a href="{{ source.url }}" class="source-link" target="_blank">
                                    {{ source.title or source.url }}
                                </a>
                            </div>
                            {% endfor %}
                        </div>
                    </div>
                    {% else %}
                    <div class="summary-section">
                        <h2>ℹ️ No New Content</h2>
                        <p>No new content was found from your monitored sources today.</p>
                    </div>
                    {% endif %}
                </div>

                <div class="footer">
                    <p>This email was generated automatically by your AI Assistant Agent.</p>
                    <p>To modify your monitored sources or email preferences, please access your dashboard.</p>
                </div>
            </body>
            </html>
        """

        # Topic summary template
        topic_summary_template = """
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="utf-8">
                <title>Topic Summary: {{ topic }}</title>
                <style>
                    body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
                    .header { background-color: #f4f4f4; padding: 20px; text-align: center; }
                    .content { padding: 20px; }
                    .topic-highlight { background-color: #007cba; color: white; padding: 10px; border-radius: 5px; display: inline-block; }
                    .summary-section { margin-bottom: 30px; }
                    .source-list { background-color: #f9f9f9; padding: 15px; border-left: 4px solid #28a745; }
                    .source-item { margin-bottom: 10px; }
                    .source-link { color: #007cba; text-decoration: none; }
                    .source-link:hover { text-decoration: underline; }
                    .stats { background-color: #e8f4f8; padding: 15px; border-radius: 5px; }
                    .footer { background-color: #f4f4f4; padding: 15px; text-align: center; font-size: 12px; color: #666; }
                </style>
            </head>
            <body>
                <div class="header">
                    <h1>🎯 Topic Summary</h1>
                    <div class="topic-highlight">{{ topic }}</div>
                    <p>{{ generated_date }}</p>
                </div>

                <div class="content">
                    <div class="stats">
                        <h3>📊 Summary Statistics</h3>
                        <ul>
                            <li><strong>Topic:</strong> {{ topic }}</li>
                            <li><strong>Content Items Found:</strong> {{ content_count }}</li>
                            <li><strong>Time Period:</strong> Last {{ period_days }} days</li>
                            <li><strong>Generated At:</strong> {{ generated_at }}</li>
                        </ul>
                    </div>

                    {% if content_count > 0 %}
                    <div class="summary-section">
                        <h2>📝 Topic Analysis</h2>
                        <div>
                            {{ summary|safe }}
                        </div>
                    </div>

                    <div class="summary-section">
                        <h2>🔗 Related Sources</h2>
                        <div class="source-list">
                            {% for source in sources %}
                            <div class="source-item">
                                <a href="{{ source.url }}" class="source-link" target="_blank">
                                    {{ source.title or source.url }}
                                </a>
                            </div>
                            {% endfor %}
                        </div>
                    </div>
                    {% else %}
                    <div class="summary-section">
                        <h2>ℹ️ No Content Found</h2>
                        <p>No content related to "{{ topic }}" was found in the specified time period.</p>
                    </div>
                    {% endif %}
                </div>

                <div class="footer">
                    <p>This topic summary was generated automatically by your AI Assistant Agent.</p>
                </div>
            </body>
            </html>
        """

        # Alert template
        alert_template = """
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="utf-8">
                <title>AI Assistant Alert</title>
                <style>
                    body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
                    .header { background-color: #dc3545; color: white; padding: 20px; text-align: center; }
                    .content { padding: 20px; }
                    .alert-section { background-color: #f8d7da; border: 1px solid #f5c6cb; padding: 15px; border-radius: 5px; margin-bottom: 20px; }
                    .alert-item { margin-bottom: 10px; padding: 10px; background-color: white; border-radius: 3px; }
                    .timestamp { color: #666; font-size: 12px; }
                    .footer { background-color: #f4f4f4; padding: 15px; text-align: center; font-size: 12px; color: #666; }
                </style>
            </head>
            <body>
                <div class="header">
                    <h1>⚠️ AI Assistant Alert</h1>
                    <p>System Alert Notification</p>
                </div>

                <div class="content">
                    <div class="alert-section">
                        <h2>🚨 Alerts</h2>
                        {% for alert in alerts %}
                        <div class="alert-item">
                            <strong>{{ alert.type or 'System Alert' }}:</strong> {{ alert.message }}
                            {% if alert.timestamp %}
                            <div class="timestamp">{{ alert.timestamp }}</div>
                            {% endif %}
                        </div>
                        {% endfor %}
                    </div>

                    {% if details %}
                    <div class="summary-section">
                        <h2>📋 Additional Details</h2>
                        <div>
                            {{ details|safe }}
                        </div>
                    </div>
                    {% endif %}
                </div>

                <div class="footer">
                    <p>This alert was generated automatically by your AI Assistant Agent.</p>
                    <p>Please check your system dashboard for more information.</p>
                </div>
            </body>
            </html>
        """

        # Write templates to files
        templates = {
            'daily_summary.html': daily_summary_template,
            'topic_summary.html': topic_summary_template,
            'alert.html': alert_template
        }

        for filename, content in templates.items():
            template_path = template_dir / filename
            if not template_path.exists():
                with open(template_path, 'w', encoding='utf-8') as f:
                    f.write(content.strip())
                self.logger.info(f"Created default template: {filename}")

    async def send_daily_summary(self, summary_data: Dict[str, Any]) -> bool:
        """
        Send daily content summary email

        Args:
            summary_data: Dictionary containing summary information

        Returns:
            Success status
        """
        try:
            # Prepare template data
            template_data = {
                'generated_date': datetime.now().strftime('%B %d, %Y'),
                'generated_at': summary_data.get('generated_at', datetime.now().isoformat()),
                'content_count': summary_data.get('content_count', 0),
                'summary': self._format_summary_text(summary_data.get('summary', '')),
                'sources': summary_data.get('sources', []),
                'topic_filter': summary_data.get('topic_filter')
            }

            # Generate email content
            subject = f"Daily Content Summary - {template_data['generated_date']}"
            if template_data['topic_filter']:
                subject += f" ({template_data['topic_filter']})"

            html_content = self._render_template('daily_summary.html', template_data)
            text_content = self._generate_text_summary(summary_data)

            # Send email
            success = await self._send_email(
                subject=subject,
                html_content=html_content,
                text_content=text_content,
                recipients=self.recipients
            )

            if success:
                self.logger.info(f"Daily summary email sent to {len(self.recipients)} recipients")

            return success

        except Exception as e:
            self.logger.error(f"Error sending daily summary email: {e}")
            return False

    async def send_topic_summary(self, topic_data: Dict[str, Any]) -> bool:
        """
        Send topic-specific summary email

        Args:
            topic_data: Dictionary containing topic summary information

        Returns:
            Success status
        """
        try:
            # Prepare template data
            template_data = {
                'generated_date': datetime.now().strftime('%B %d, %Y'),
                'topic': topic_data.get('topic', 'Unknown Topic'),
                'generated_at': topic_data.get('generated_at', datetime.now().isoformat()),
                'content_count': topic_data.get('content_count', 0),
                'period_days': topic_data.get('period_days', 7),
                'summary': self._format_summary_text(topic_data.get('summary', '')),
                'sources': topic_data.get('sources', [])
            }

            # Generate email content
            subject = f"Topic Summary: {template_data['topic']} - {template_data['generated_date']}"

            html_content = self._render_template('topic_summary.html', template_data)
            text_content = self._generate_topic_text_summary(topic_data)

            # Send email
            success = await self._send_email(
                subject=subject,
                html_content=html_content,
                text_content=text_content,
                recipients=self.recipients
            )

            if success:
                self.logger.info(f"Topic summary email sent for '{template_data['topic']}'")

            return success

        except Exception as e:
            self.logger.error(f"Error sending topic summary email: {e}")
            return False

    async def send_alert_email(self, alerts: List[Dict[str, Any]],
                              details: str = None) -> bool:
        """
        Send system alert email

        Args:
            alerts: List of alert dictionaries
            details: Additional details about the alerts

        Returns:
            Success status
        """
        try:
            # Prepare template data
            template_data = {
                'alerts': alerts,
                'details': details,
                'timestamp': datetime.now().strftime('%B %d, %Y at %I:%M %p')
            }

            # Generate email content
            alert_count = len(alerts)
            subject = f"AI Assistant Alert - {alert_count} Alert{'s' if alert_count != 1 else ''}"

            html_content = self._render_template('alert.html', template_data)
            text_content = self._generate_alert_text(alerts, details)

            # Send email with high priority
            success = await self._send_email(
                subject=subject,
                html_content=html_content,
                text_content=text_content,
                recipients=self.recipients,
                priority='high'
            )

            if success:
                self.logger.info(f"Alert email sent for {alert_count} alerts")

            return success

        except Exception as e:
            self.logger.error(f"Error sending alert email: {e}")
            return False

    async def send_custom_email(self, subject: str, content: str,
                               recipients: List[str] = None,
                               html_content: str = None,
                               attachments: List[str] = None) -> bool:
        """
        Send custom email

        Args:
            subject: Email subject
            content: Plain text content
            recipients: List of recipient emails (uses default if None)
            html_content: Optional HTML content
            attachments: List of file paths to attach

        Returns:
            Success status
        """
        try:
            recipients = recipients or self.recipients

            success = await self._send_email(
                subject=subject,
                text_content=content,
                html_content=html_content,
                recipients=recipients,
                attachments=attachments
            )

            if success:
                self.logger.info(f"Custom email sent to {len(recipients)} recipients")

            return success

        except Exception as e:
            self.logger.error(f"Error sending custom email: {e}")
            return False

    async def _send_email(self, subject: str, text_content: str,
                         recipients: List[str], html_content: str = None,
                         attachments: List[str] = None,
                         priority: str = 'normal') -> bool:
        """
        Internal method to send email via SMTP

        Args:
            subject: Email subject
            text_content: Plain text content
            recipients: List of recipient emails
            html_content: Optional HTML content
            attachments: Optional list of file paths to attach
            priority: Email priority (normal, high, low)

        Returns:
            Success status
        """
        try:
            # Create message
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = self.username
            msg['To'] = ', '.join(recipients)

            # Set priority
            if priority == 'high':
                msg['X-Priority'] = '1'
                msg['X-MSMail-Priority'] = 'High'
            elif priority == 'low':
                msg['X-Priority'] = '5'
                msg['X-MSMail-Priority'] = 'Low'

            # Add text content
            text_part = MIMEText(text_content, 'plain', 'utf-8')
            msg.attach(text_part)

            # Add HTML content if provided
            if html_content:
                html_part = MIMEText(html_content, 'html', 'utf-8')
                msg.attach(html_part)

            # Add attachments if provided
            if attachments:
                for file_path in attachments:
                    if os.path.exists(file_path):
                        with open(file_path, 'rb') as attachment:
                            part = MIMEBase('application', 'octet-stream')
                            part.set_payload(attachment.read())
                            encoders.encode_base64(part)
                            part.add_header(
                                'Content-Disposition',
                                f'attachment; filename= {os.path.basename(file_path)}'
                            )
                            msg.attach(part)
                    else:
                        self.logger.warning(f"Attachment file not found: {file_path}")

            # Create SMTP session
            context = ssl.create_default_context()

            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls(context=context)
                server.login(self.username, self.password)

                # Send email
                text = msg.as_string()
                server.sendmail(self.username, recipients, text)

            self.logger.info(f"Email sent successfully to {len(recipients)} recipients")
            return True

        except smtplib.SMTPAuthenticationError as e:
            self.logger.error(f"SMTP authentication failed: {e}")
            return False
        except smtplib.SMTPException as e:
            self.logger.error(f"SMTP error: {e}")
            return False
        except Exception as e:
            self.logger.error(f"Unexpected error sending email: {e}")
            return False

    def _render_template(self, template_name: str, data: Dict[str, Any]) -> str:
        """Render Jinja2 template with data"""
        try:
            template = self.jinja_env.get_template(template_name)
            return template.render(**data)
        except Exception as e:
            self.logger.error(f"Error rendering template {template_name}: {e}")
            return f"Error rendering template: {e}"

    def _format_summary_text(self, summary: str) -> str:
        """Format summary text for HTML display"""
        if not summary:
            return "No summary available."

        # Convert line breaks to HTML
        formatted = summary.replace('\n', '<br>')

        # Simple markdown-like formatting
        formatted = formatted.replace('**', '<strong>').replace('**', '</strong>')
        formatted = formatted.replace('*', '<em>').replace('*', '</em>')

        return formatted

    def _generate_text_summary(self, summary_data: Dict[str, Any]) -> str:
        """Generate plain text version of daily summary"""
        lines = [
            "AI ASSISTANT DAILY SUMMARY",
            "=" * 30,
            "",
            f"Generated: {summary_data.get('generated_at', 'Unknown')}",
            f"New Content Items: {summary_data.get('content_count', 0)}",
            ""
        ]

        if summary_data.get('content_count', 0) > 0:
            lines.extend([
                "SUMMARY:",
                "-" * 10,
                summary_data.get('summary', 'No summary available.'),
                "",
                "SOURCES:",
                "-" * 10
            ])

            for source in summary_data.get('sources', []):
                lines.append(f"• {source.get('title', source.get('url', 'Unknown'))}")
                lines.append(f"  {source.get('url', '')}")
                lines.append("")
        else:
            lines.append("No new content was found from your monitored sources today.")

        lines.extend([
            "",
            "-" * 50,
            "This email was generated automatically by your AI Assistant Agent."
        ])

        return '\n'.join(lines)

    def _generate_topic_text_summary(self, topic_data: Dict[str, Any]) -> str:
        """Generate plain text version of topic summary"""
        lines = [
            f"AI ASSISTANT TOPIC SUMMARY: {topic_data.get('topic', 'Unknown')}",
            "=" * 50,
            "",
            f"Generated: {topic_data.get('generated_at', 'Unknown')}",
            f"Content Items: {topic_data.get('content_count', 0)}",
            f"Time Period: Last {topic_data.get('period_days', 7)} days",
            ""
        ]

        if topic_data.get('content_count', 0) > 0:
            lines.extend([
                "TOPIC ANALYSIS:",
                "-" * 15,
                topic_data.get('summary', 'No summary available.'),
                "",
                "RELATED SOURCES:",
                "-" * 15
            ])

            for source in topic_data.get('sources', []):
                lines.append(f"• {source.get('title', source.get('url', 'Unknown'))}")
                lines.append(f"  {source.get('url', '')}")
                lines.append("")
        else:
            lines.append(f"No content related to '{topic_data.get('topic')}' was found.")

        lines.extend([
            "",
            "-" * 50,
            "This topic summary was generated automatically by your AI Assistant Agent."
        ])

        return '\n'.join(lines)

    def _generate_alert_text(self, alerts: List[Dict[str, Any]],
                           details: str = None) -> str:
        """Generate plain text version of alert email"""
        lines = [
            "AI ASSISTANT SYSTEM ALERT",
            "=" * 30,
            "",
            f"Alert Time: {datetime.now().strftime('%B %d, %Y at %I:%M %p')}",
            f"Number of Alerts: {len(alerts)}",
            "",
            "ALERTS:",
            "-" * 10
        ]

        for i, alert in enumerate(alerts, 1):
            lines.append(f"{i}. {alert.get('type', 'System Alert')}: {alert.get('message', 'No message')}")
            if alert.get('timestamp'):
                lines.append(f"   Time: {alert['timestamp']}")
            lines.append("")

        if details:
            lines.extend([
                "ADDITIONAL DETAILS:",
                "-" * 20,
                details,
                ""
            ])

        lines.extend([
            "-" * 50,
            "This alert was generated automatically by your AI Assistant Agent.",
            "Please check your system dashboard for more information."
        ])

        return '\n'.join(lines)

    def test_connection(self) -> bool:
        """
        Test SMTP connection and authentication

        Returns:
            True if connection successful, False otherwise
        """
        try:
            context = ssl.create_default_context()

            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls(context=context)
                server.login(self.username, self.password)

            self.logger.info("SMTP connection test successful")
            return True

        except Exception as e:
            self.logger.error(f"SMTP connection test failed: {e}")
            return False

    def add_recipient(self, email: str) -> bool:
        """
        Add a new recipient to the default list

        Args:
            email: Email address to add

        Returns:
            Success status
        """
        if email not in self.recipients:
            self.recipients.append(email)
            self.logger.info(f"Added recipient: {email}")
            return True
        else:
            self.logger.info(f"Recipient already exists: {email}")
            return False

    def remove_recipient(self, email: str) -> bool:
        """
        Remove a recipient from the default list

        Args:
            email: Email address to remove

        Returns:
            Success status
        """
        if email in self.recipients:
            self.recipients.remove(email)
            self.logger.info(f"Removed recipient: {email}")
            return True
        else:
            self.logger.info(f"Recipient not found: {email}")
            return False

    def get_recipients(self) -> List[str]:
        """
        Get current list of recipients

        Returns:
            List of recipient email addresses
        """
        return self.recipients.copy()

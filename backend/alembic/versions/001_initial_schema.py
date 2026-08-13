"""Initial Schema Migration

Revision ID: 001_initial_schema
Revises: 
Create Date: 2026-08-11 14:30:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '001_initial_schema'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Users table
    op.create_table(
        'users',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('role', sa.Enum('ADMIN', 'REVIEWER', 'VIEWER', name='userrole'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_users_email'), 'users', ['email'], unique=True)

    # Documents table
    op.create_table(
        'documents',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('filename', sa.String(length=255), nullable=False),
        sa.Column('file_path', sa.String(length=512), nullable=False),
        sa.Column('file_type', sa.String(length=50), nullable=False),
        sa.Column('upload_date', sa.DateTime(timezone=True), nullable=False),
        sa.Column('uploaded_by', sa.String(length=36), nullable=True),
        sa.Column('status', sa.Enum('UPLOADED', 'PROCESSING', 'PREPROCESSED', 'OCR_COMPLETE', 'CLASSIFIED', 'EXTRACTED', 'VALIDATED', 'NEEDS_REVIEW', 'FAILED', name='documentstatus'), nullable=False),
        sa.Column('document_type', sa.Enum('INVOICE', 'CONTRACT', 'FORM', 'REPORT', 'RECEIPT', 'PURCHASE_ORDER', 'OTHER', name='documenttype'), nullable=False),
        sa.Column('page_count', sa.Integer(), nullable=False),
        sa.Column('raw_text', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['uploaded_by'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_documents_document_type'), 'documents', ['document_type'], unique=False)
    op.create_index(op.f('ix_documents_status'), 'documents', ['status'], unique=False)

    # Extracted fields table
    op.create_table(
        'extracted_fields',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('document_id', sa.String(length=36), nullable=False),
        sa.Column('field_name', sa.String(length=255), nullable=False),
        sa.Column('field_value', sa.Text(), nullable=True),
        sa.Column('confidence_score', sa.Float(), nullable=False),
        sa.Column('data_type', sa.Enum('STRING', 'DATE', 'NUMBER', 'CURRENCY', 'JSON', 'BOOLEAN', name='datatype'), nullable=False),
        sa.Column('bounding_box', sa.JSON(), nullable=True),
        sa.Column('is_validated', sa.Boolean(), nullable=False),
        sa.Column('validation_notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['document_id'], ['documents.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_extracted_fields_document_id'), 'extracted_fields', ['document_id'], unique=False)
    op.create_index(op.f('ix_extracted_fields_field_name'), 'extracted_fields', ['field_name'], unique=False)

    # Document classifications table
    op.create_table(
        'document_classifications',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('document_id', sa.String(length=36), nullable=False),
        sa.Column('predicted_type', sa.Enum('INVOICE', 'CONTRACT', 'FORM', 'REPORT', 'RECEIPT', 'PURCHASE_ORDER', 'OTHER', name='documenttype'), nullable=False),
        sa.Column('confidence_score', sa.Float(), nullable=False),
        sa.Column('model_used', sa.String(length=255), nullable=False),
        sa.Column('classified_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['document_id'], ['documents.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_document_classifications_document_id'), 'document_classifications', ['document_id'], unique=True)

    # Validation results table
    op.create_table(
        'validation_results',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('document_id', sa.String(length=36), nullable=False),
        sa.Column('field_id', sa.String(length=36), nullable=True),
        sa.Column('rule_name', sa.String(length=255), nullable=False),
        sa.Column('passed', sa.Boolean(), nullable=False),
        sa.Column('severity', sa.Enum('ERROR', 'WARNING', 'INFO', name='validationseverity'), nullable=False),
        sa.Column('message', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['document_id'], ['documents.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['field_id'], ['extracted_fields.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_validation_results_document_id'), 'validation_results', ['document_id'], unique=False)

    # Processing logs table
    op.create_table(
        'processing_logs',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('document_id', sa.String(length=36), nullable=False),
        sa.Column('stage', sa.Enum('UPLOAD', 'PREPROCESSING', 'OCR', 'CLASSIFICATION', 'EXTRACTION', 'VALIDATION', 'EXPORT', name='processingstage'), nullable=False),
        sa.Column('status', sa.String(length=50), nullable=False),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['document_id'], ['documents.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_processing_logs_document_id'), 'processing_logs', ['document_id'], unique=False)


def downgrade() -> None:
    op.drop_table('processing_logs')
    op.drop_table('validation_results')
    op.drop_table('document_classifications')
    op.drop_table('extracted_fields')
    op.drop_table('documents')
    op.drop_table('users')

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import json
import os
import logging
from typing import Dict, List, Any, Optional, Union
from datetime import datetime
import io
import base64
from pathlib import Path
import csv

logger = logging.getLogger(__name__)

class DataAnalyzer:
    """
    Handles data analysis operations including CSV processing, 
    statistical analysis, and visualization generation.
    """
    
    def __init__(self, output_dir: str = "/usr/src/app/data/output"):
        """
        Initialize data analyzer.
        
        Args:
            output_dir: Directory to save analysis results and visualizations
        """
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
        
        # Set up matplotlib for headless operation
        plt.style.use('default')
        plt.ioff()  # Turn off interactive mode

    def load_data(self, file_path: str) -> Dict[str, Any]:
        """
        Load data from various file formats (CSV, JSON, Excel).
        
        Args:
            file_path: Path to the data file
            
        Returns:
            Dictionary with loaded data and metadata
        """
        try:
            if not os.path.exists(file_path):
                return {"status": "error", "message": f"File not found: {file_path}"}
            
            file_extension = Path(file_path).suffix.lower()
            
            if file_extension == '.csv':
                df = pd.read_csv(file_path)
                data_type = "CSV"
            elif file_extension in ['.xlsx', '.xls']:
                df = pd.read_excel(file_path)
                data_type = "Excel"
            elif file_extension == '.json':
                df = pd.read_json(file_path)
                data_type = "JSON"
            else:
                return {"status": "error", "message": f"Unsupported file format: {file_extension}"}
            
            # Basic data info
            info = {
                "status": "success",
                "data_type": data_type,
                "shape": df.shape,
                "columns": df.columns.tolist(),
                "dtypes": df.dtypes.to_dict(),
                "missing_values": df.isnull().sum().to_dict(),
                "memory_usage": df.memory_usage(deep=True).sum(),
                "file_path": file_path,
                "sample_data": df.head().to_dict('records') if len(df) > 0 else []
            }
            
            # Store dataframe for further analysis
            setattr(self, f'df_{datetime.now().timestamp()}', df)
            
            logger.info(f"Loaded {data_type} file with shape {df.shape}")
            return info
            
        except Exception as e:
            error_msg = f"Failed to load data from {file_path}: {e}"
            logger.error(error_msg)
            return {"status": "error", "message": str(e)}

    def analyze_csv(self, file_path: str, generate_visualizations: bool = True) -> Dict[str, Any]:
        """
        Perform comprehensive analysis of a CSV file.
        
        Args:
            file_path: Path to the CSV file
            generate_visualizations: Whether to generate visualization files
            
        Returns:
            Dictionary with analysis results
        """
        try:
            # Load data
            load_result = self.load_data(file_path)
            if load_result["status"] == "error":
                return load_result
            
            df = pd.read_csv(file_path)
            
            # Basic statistics
            analysis = {
                "status": "success",
                "file_info": {
                    "name": os.path.basename(file_path),
                    "size_mb": os.path.getsize(file_path) / (1024 * 1024),
                    "rows": len(df),
                    "columns": len(df.columns)
                },
                "data_summary": {
                    "numeric_columns": df.select_dtypes(include=[np.number]).columns.tolist(),
                    "categorical_columns": df.select_dtypes(include=['object']).columns.tolist(),
                    "datetime_columns": df.select_dtypes(include=['datetime64']).columns.tolist(),
                    "missing_data": df.isnull().sum().to_dict(),
                    "duplicate_rows": int(df.duplicated().sum())
                }
            }
            
            # Statistical analysis for numeric columns
            numeric_stats = {}
            for col in analysis["data_summary"]["numeric_columns"]:
                try:
                    stats = {
                        "count": int(df[col].count()),
                        "mean": float(df[col].mean()) if not df[col].isna().all() else None,
                        "std": float(df[col].std()) if not df[col].isna().all() else None,
                        "min": float(df[col].min()) if not df[col].isna().all() else None,
                        "max": float(df[col].max()) if not df[col].isna().all() else None,
                        "median": float(df[col].median()) if not df[col].isna().all() else None,
                        "q25": float(df[col].quantile(0.25)) if not df[col].isna().all() else None,
                        "q75": float(df[col].quantile(0.75)) if not df[col].isna().all() else None,
                        "skewness": float(df[col].skew()) if not df[col].isna().all() else None,
                        "kurtosis": float(df[col].kurtosis()) if not df[col].isna().all() else None
                    }
                    numeric_stats[col] = stats
                except Exception as e:
                    logger.warning(f"Error calculating stats for column {col}: {e}")
                    numeric_stats[col] = {"error": str(e)}
            
            analysis["numeric_statistics"] = numeric_stats
            
            # Categorical analysis
            categorical_stats = {}
            for col in analysis["data_summary"]["categorical_columns"]:
                try:
                    value_counts = df[col].value_counts()
                    categorical_stats[col] = {
                        "unique_values": int(df[col].nunique()),
                        "most_frequent": str(value_counts.index[0]) if len(value_counts) > 0 else None,
                        "most_frequent_count": int(value_counts.iloc[0]) if len(value_counts) > 0 else 0,
                        "top_5_values": value_counts.head().to_dict()
                    }
                except Exception as e:
                    logger.warning(f"Error analyzing categorical column {col}: {e}")
                    categorical_stats[col] = {"error": str(e)}
            
            analysis["categorical_statistics"] = categorical_stats
            
            # Generate visualizations if requested
            if generate_visualizations:
                viz_results = self.generate_visualizations(df, file_path)
                analysis["visualizations"] = viz_results
            
            # Data quality insights
            analysis["data_quality"] = self._assess_data_quality(df)
            
            # Correlation analysis for numeric data
            if len(analysis["data_summary"]["numeric_columns"]) > 1:
                try:
                    numeric_df = df[analysis["data_summary"]["numeric_columns"]]
                    correlation_matrix = numeric_df.corr()
                    analysis["correlations"] = correlation_matrix.to_dict()
                except Exception as e:
                    logger.warning(f"Error calculating correlations: {e}")
                    analysis["correlations"] = {"error": str(e)}
            
            logger.info(f"Completed analysis of CSV file: {file_path}")
            return analysis
            
        except Exception as e:
            error_msg = f"Failed to analyze CSV file {file_path}: {e}"
            logger.error(error_msg)
            return {"status": "error", "message": str(e)}

    def _assess_data_quality(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Assess the quality of the dataset"""
        try:
            total_cells = df.shape[0] * df.shape[1]
            missing_cells = df.isnull().sum().sum()
            
            quality_assessment = {
                "completeness": {
                    "percentage": round(((total_cells - missing_cells) / total_cells) * 100, 2),
                    "missing_cells": int(missing_cells),
                    "total_cells": int(total_cells)
                },
                "consistency": {
                    "duplicate_rows": int(df.duplicated().sum()),
                    "duplicate_percentage": round((df.duplicated().sum() / len(df)) * 100, 2)
                },
                "column_issues": {}
            }
            
            # Check for potential issues in each column
            for col in df.columns:
                issues = []
                
                # Check for high missing values
                missing_pct = (df[col].isnull().sum() / len(df)) * 100
                if missing_pct > 50:
                    issues.append(f"High missing values ({missing_pct:.1f}%)")
                
                # Check for single value columns
                if df[col].nunique() == 1:
                    issues.append("All values are identical")
                
                # Check for potential outliers in numeric columns
                if df[col].dtype in ['int64', 'float64']:
                    q1 = df[col].quantile(0.25)
                    q3 = df[col].quantile(0.75)
                    iqr = q3 - q1
                    outliers = len(df[(df[col] < (q1 - 1.5 * iqr)) | (df[col] > (q3 + 1.5 * iqr))])
                    if outliers > 0:
                        issues.append(f"Potential outliers detected ({outliers} values)")
                
                if issues:
                    quality_assessment["column_issues"][col] = issues
            
            return quality_assessment
            
        except Exception as e:
            logger.error(f"Error assessing data quality: {e}")
            return {"error": str(e)}

    def generate_visualizations(self, df: pd.DataFrame, source_file: str) -> Dict[str, Any]:
        """
        Generate various visualizations for the dataset.
        
        Args:
            df: pandas DataFrame
            source_file: Source file path for naming output files
            
        Returns:
            Dictionary with visualization file paths and info
        """
        try:
            visualizations = {"status": "success", "generated_files": []}
            
            # Create output directory for visualizations
            viz_dir = os.path.join(self.output_dir, "visualizations")
            os.makedirs(viz_dir, exist_ok=True)
            
            base_name = Path(source_file).stem
            
            # 1. Data overview (missing values heatmap)
            if df.isnull().sum().sum() > 0:
                plt.figure(figsize=(12, 8))
                sns.heatmap(df.isnull(), cbar=True, cmap='viridis')
                plt.title('Missing Values Heatmap')
                plt.tight_layout()
                
                missing_file = os.path.join(viz_dir, f"{base_name}_missing_values.png")
                plt.savefig(missing_file, dpi=300, bbox_inches='tight')
                plt.close()
                
                visualizations["generated_files"].append({
                    "type": "missing_values_heatmap",
                    "file_path": missing_file,
                    "description": "Heatmap showing missing values in the dataset"
                })
            
            # 2. Numeric columns - histograms and box plots
            numeric_cols = df.select_dtypes(include=[np.number]).columns
            if len(numeric_cols) > 0:
                # Histograms
                n_cols = min(3, len(numeric_cols))
                n_rows = (len(numeric_cols) + n_cols - 1) // n_cols
                
                fig, axes = plt.subplots(n_rows, n_cols, figsize=(15, 5*n_rows))
                if n_rows == 1 and n_cols == 1:
                    axes = [axes]
                elif n_rows == 1:
                    axes = axes.flatten()
                elif n_cols == 1:
                    axes = axes.flatten()
                else:
                    axes = axes.flatten()
                
                for i, col in enumerate(numeric_cols):
                    if i < len(axes):
                        df[col].hist(ax=axes[i], bins=30, edgecolor='black')
                        axes[i].set_title(f'Distribution of {col}')
                        axes[i].set_xlabel(col)
                        axes[i].set_ylabel('Frequency')
                
                # Hide empty subplots
                for i in range(len(numeric_cols), len(axes)):
                    axes[i].set_visible(False)
                
                plt.tight_layout()
                hist_file = os.path.join(viz_dir, f"{base_name}_histograms.png")
                plt.savefig(hist_file, dpi=300, bbox_inches='tight')
                plt.close()
                
                visualizations["generated_files"].append({
                    "type": "histograms",
                    "file_path": hist_file,
                    "description": "Histograms for all numeric columns"
                })
                
                # Box plots
                if len(numeric_cols) <= 6:  # Only if manageable number of columns
                    plt.figure(figsize=(12, 8))
                    df[numeric_cols].boxplot()
                    plt.title('Box Plots for Numeric Columns')
                    plt.xticks(rotation=45)
                    plt.tight_layout()
                    
                    box_file = os.path.join(viz_dir, f"{base_name}_boxplots.png")
                    plt.savefig(box_file, dpi=300, bbox_inches='tight')
                    plt.close()
                    
                    visualizations["generated_files"].append({
                        "type": "boxplots",
                        "file_path": box_file,
                        "description": "Box plots showing distribution and outliers"
                    })
            
            # 3. Correlation heatmap
            if len(numeric_cols) > 1:
                plt.figure(figsize=(10, 8))
                correlation_matrix = df[numeric_cols].corr()
                sns.heatmap(correlation_matrix, annot=True, cmap='coolwarm', center=0, 
                           square=True, linewidths=0.5)
                plt.title('Correlation Matrix')
                plt.tight_layout()
                
                corr_file = os.path.join(viz_dir, f"{base_name}_correlation.png")
                plt.savefig(corr_file, dpi=300, bbox_inches='tight')
                plt.close()
                
                visualizations["generated_files"].append({
                    "type": "correlation_heatmap",
                    "file_path": corr_file,
                    "description": "Correlation matrix for numeric variables"
                })
            
            # 4. Categorical columns - bar charts
            categorical_cols = df.select_dtypes(include=['object']).columns
            for col in categorical_cols[:3]:  # Limit to first 3 categorical columns
                if df[col].nunique() <= 10:  # Only for columns with reasonable number of categories
                    plt.figure(figsize=(10, 6))
                    value_counts = df[col].value_counts()
                    value_counts.plot(kind='bar')
                    plt.title(f'Distribution of {col}')
                    plt.xlabel(col)
                    plt.ylabel('Count')
                    plt.xticks(rotation=45)
                    plt.tight_layout()
                    
                    bar_file = os.path.join(viz_dir, f"{base_name}_{col}_distribution.png")
                    plt.savefig(bar_file, dpi=300, bbox_inches='tight')
                    plt.close()
                    
                    visualizations["generated_files"].append({
                        "type": "categorical_distribution",
                        "file_path": bar_file,
                        "description": f"Distribution of categorical variable: {col}"
                    })
            
            logger.info(f"Generated {len(visualizations['generated_files'])} visualizations")
            return visualizations
            
        except Exception as e:
            error_msg = f"Failed to generate visualizations: {e}"
            logger.error(error_msg)
            return {"status": "error", "message": str(e)}

    def generate_report(self, analysis_result: Dict[str, Any], 
                       report_format: str = "json") -> Dict[str, Any]:
        """
        Generate a comprehensive analysis report.
        
        Args:
            analysis_result: Result from analyze_csv method
            report_format: Format for the report ('json', 'html', 'txt')
            
        Returns:
            Dictionary with report file path and summary
        """
        try:
            if analysis_result.get("status") != "success":
                return {"status": "error", "message": "Invalid analysis result provided"}
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            file_name = analysis_result["file_info"]["name"]
            base_name = Path(file_name).stem
            
            report_data = {
                "report_metadata": {
                    "generated_at": datetime.now().isoformat(),
                    "source_file": file_name,
                    "analysis_timestamp": timestamp
                },
                "executive_summary": self._generate_executive_summary(analysis_result),
                "detailed_analysis": analysis_result
            }
            
            if report_format.lower() == "json":
                report_file = os.path.join(self.output_dir, f"{base_name}_analysis_report_{timestamp}.json")
                with open(report_file, 'w') as f:
                    json.dump(report_data, f, indent=2, default=str)
                    
            elif report_format.lower() == "html":
                report_file = os.path.join(self.output_dir, f"{base_name}_analysis_report_{timestamp}.html")
                html_content = self._generate_html_report(report_data)
                with open(report_file, 'w') as f:
                    f.write(html_content)
                    
            elif report_format.lower() == "txt":
                report_file = os.path.join(self.output_dir, f"{base_name}_analysis_report_{timestamp}.txt")
                txt_content = self._generate_text_report(report_data)
                with open(report_file, 'w') as f:
                    f.write(txt_content)
            else:
                return {"status": "error", "message": f"Unsupported report format: {report_format}"}
            
            return {
                "status": "success",
                "report_file": report_file,
                "format": report_format,
                "summary": report_data["executive_summary"],
                "message": f"Report generated successfully: {os.path.basename(report_file)}"
            }
            
        except Exception as e:
            error_msg = f"Failed to generate report: {e}"
            logger.error(error_msg)
            return {"status": "error", "message": str(e)}

    def _generate_executive_summary(self, analysis_result: Dict[str, Any]) -> Dict[str, Any]:
        """Generate executive summary from analysis results"""
        try:
            file_info = analysis_result["file_info"]
            data_summary = analysis_result["data_summary"]
            quality = analysis_result.get("data_quality", {})
            
            # Key insights
            insights = []
            
            # Data size insight
            if file_info["rows"] > 10000:
                insights.append(f"Large dataset with {file_info['rows']:,} records")
            elif file_info["rows"] < 100:
                insights.append(f"Small dataset with only {file_info['rows']} records")
            
            # Missing data insight
            missing_pct = quality.get("completeness", {}).get("percentage", 100)
            if missing_pct < 90:
                insights.append(f"Data completeness is {missing_pct}% - significant missing values detected")
            elif missing_pct > 99:
                insights.append("Excellent data completeness with minimal missing values")
            
            # Duplicate data insight
            dup_pct = quality.get("consistency", {}).get("duplicate_percentage", 0)
            if dup_pct > 5:
                insights.append(f"High duplicate rate detected ({dup_pct}%)")
            
            # Column diversity insight
            if len(data_summary["numeric_columns"]) > len(data_summary["categorical_columns"]):
                insights.append("Dataset is primarily numeric - suitable for statistical analysis")
            elif len(data_summary["categorical_columns"]) > len(data_summary["numeric_columns"]):
                insights.append("Dataset is primarily categorical - suitable for classification analysis")
            
            return {
                "dataset_overview": {
                    "name": file_info["name"],
                    "size": f"{file_info['rows']:,} rows × {file_info['columns']} columns",
                    "file_size": f"{file_info['size_mb']:.2f} MB"
                },
                "data_composition": {
                    "numeric_columns": len(data_summary["numeric_columns"]),
                    "categorical_columns": len(data_summary["categorical_columns"]),
                    "datetime_columns": len(data_summary["datetime_columns"])
                },
                "key_insights": insights,
                "data_quality_score": missing_pct,
                "recommendations": self._generate_recommendations(analysis_result)
            }
            
        except Exception as e:
            logger.error(f"Error generating executive summary: {e}")
            return {"error": str(e)}

    def _generate_recommendations(self, analysis_result: Dict[str, Any]) -> List[str]:
        """Generate actionable recommendations based on analysis"""
        recommendations = []
        
        try:
            data_summary = analysis_result["data_summary"]
            quality = analysis_result.get("data_quality", {})
            
            # Missing data recommendations
            missing_pct = quality.get("completeness", {}).get("percentage", 100)
            if missing_pct < 95:
                recommendations.append("Consider data imputation or removal of incomplete records")
            
            # Duplicate data recommendations
            dup_count = quality.get("consistency", {}).get("duplicate_rows", 0)
            if dup_count > 0:
                recommendations.append(f"Remove {dup_count} duplicate rows to improve data quality")
            
            # Column-specific recommendations
            column_issues = quality.get("column_issues", {})
            if column_issues:
                recommendations.append("Review flagged columns for data quality issues")
            
            # Analysis recommendations
            if len(data_summary["numeric_columns"]) > 1:
                recommendations.append("Explore correlations between numeric variables for insights")
            
            if len(data_summary["categorical_columns"]) > 0:
                recommendations.append("Analyze categorical distributions for pattern identification")
            
            # Visualization recommendations
            if len(data_summary["numeric_columns"]) > 0:
                recommendations.append("Generate histograms and box plots to understand distributions")
            
        except Exception as e:
            logger.error(f"Error generating recommendations: {e}")
        
        return recommendations

    def _generate_html_report(self, report_data: Dict[str, Any]) -> str:
        """Generate HTML format report"""
        summary = report_data["executive_summary"]
        analysis = report_data["detailed_analysis"]
        
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Data Analysis Report</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 40px; }}
                h1, h2, h3 {{ color: #333; }}
                .summary {{ background: #f8f9fa; padding: 20px; border-radius: 8px; margin: 20px 0; }}
                .metric {{ display: inline-block; margin: 10px 20px; }}
                .insight {{ background: #e3f2fd; padding: 10px; margin: 5px 0; border-left: 4px solid #2196f3; }}
                .recommendation {{ background: #fff3e0; padding: 10px; margin: 5px 0; border-left: 4px solid #ff9800; }}
                table {{ border-collapse: collapse; width: 100%; margin: 20px 0; }}
                th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
                th {{ background-color: #f2f2f2; }}
            </style>
        </head>
        <body>
            <h1>Data Analysis Report</h1>
            <p><strong>Dataset:</strong> {summary["dataset_overview"]["name"]}</p>
            <p><strong>Generated:</strong> {report_data["report_metadata"]["generated_at"]}</p>
            
            <div class="summary">
                <h2>Executive Summary</h2>
                <div class="metric"><strong>Size:</strong> {summary["dataset_overview"]["size"]}</div>
                <div class="metric"><strong>File Size:</strong> {summary["dataset_overview"]["file_size"]}</div>
                <div class="metric"><strong>Data Quality:</strong> {summary["data_quality_score"]:.1f}%</div>
                
                <h3>Key Insights</h3>
                {''.join(f'<div class="insight">{insight}</div>' for insight in summary["key_insights"])}
                
                <h3>Recommendations</h3>
                {''.join(f'<div class="recommendation">{rec}</div>' for rec in summary["recommendations"])}
            </div>
            
            <h2>Data Composition</h2>
            <table>
                <tr><th>Type</th><th>Count</th></tr>
                <tr><td>Numeric Columns</td><td>{summary["data_composition"]["numeric_columns"]}</td></tr>
                <tr><td>Categorical Columns</td><td>{summary["data_composition"]["categorical_columns"]}</td></tr>
                <tr><td>DateTime Columns</td><td>{summary["data_composition"]["datetime_columns"]}</td></tr>
            </table>
        </body>
        </html>
        """
        return html

    def _generate_text_report(self, report_data: Dict[str, Any]) -> str:
        """Generate text format report"""
        summary = report_data["executive_summary"]
        lines = [
            "=" * 50,
            "DATA ANALYSIS REPORT",
            "=" * 50,
            "",
            f"Dataset: {summary['dataset_overview']['name']}",
            f"Generated: {report_data['report_metadata']['generated_at']}",
            "",
            "EXECUTIVE SUMMARY",
            "-" * 20,
            f"Size: {summary['dataset_overview']['size']}",
            f"File Size: {summary['dataset_overview']['file_size']}",
            f"Data Quality Score: {summary['data_quality_score']:.1f}%",
            "",
            "KEY INSIGHTS:",
        ]
        
        for insight in summary["key_insights"]:
            lines.append(f"• {insight}")
        
        lines.extend([
            "",
            "RECOMMENDATIONS:",
        ])
        
        for rec in summary["recommendations"]:
            lines.append(f"• {rec}")
        
        lines.extend([
            "",
            "DATA COMPOSITION",
            "-" * 20,
            f"Numeric Columns: {summary['data_composition']['numeric_columns']}",
            f"Categorical Columns: {summary['data_composition']['categorical_columns']}",
            f"DateTime Columns: {summary['data_composition']['datetime_columns']}",
            "",
            "=" * 50
        ])
        
        return "\n".join(lines)

    def compare_datasets(self, file_paths: List[str]) -> Dict[str, Any]:
        """
        Compare multiple datasets and provide insights.
        
        Args:
            file_paths: List of file paths to compare
            
        Returns:
            Dictionary with comparison results
        """
        try:
            if len(file_paths) < 2:
                return {"status": "error", "message": "At least 2 files required for comparison"}
            
            datasets = {}
            
            # Load all datasets
            for i, file_path in enumerate(file_paths):
                try:
                    df = pd.read_csv(file_path)  # Assuming CSV for simplicity
                    datasets[f"dataset_{i+1}"] = {
                        "name": os.path.basename(file_path),
                        "dataframe": df,
                        "shape": df.shape,
                        "columns": df.columns.tolist(),
                        "dtypes": df.dtypes.to_dict()
                    }
                except Exception as e:
                    logger.error(f"Failed to load {file_path}: {e}")
                    continue
            
            if len(datasets) < 2:
                return {"status": "error", "message": "Failed to load sufficient datasets for comparison"}
            
            # Comparison analysis
            comparison = {
                "status": "success",
                "datasets_compared": len(datasets),
                "size_comparison": {},
                "column_comparison": {},
                "schema_compatibility": {}
            }
            
            # Size comparison
            for name, data in datasets.items():
                comparison["size_comparison"][name] = {
                    "name": data["name"],
                    "rows": data["shape"][0],
                    "columns": data["shape"][1]
                }
            
            # Column comparison
            all_columns = set()
            for data in datasets.values():
                all_columns.update(data["columns"])
            
            column_matrix = {}
            for col in all_columns:
                column_matrix[col] = {}
                for name, data in datasets.items():
                    column_matrix[col][name] = col in data["columns"]
            
            comparison["column_comparison"] = column_matrix
            
            # Find common columns
            common_columns = set(list(datasets.values())[0]["columns"])
            for data in list(datasets.values())[1:]:
                common_columns = common_columns.intersection(set(data["columns"]))
            
            comparison["common_columns"] = list(common_columns)
            comparison["unique_columns"] = {}
            
            for name, data in datasets.items():
                unique = set(data["columns"]) - common_columns
                comparison["unique_columns"][name] = list(unique)
            
            # Schema compatibility
            if len(common_columns) > 0:
                schema_issues = {}
                for col in common_columns:
                    dtypes = {}
                    for name, data in datasets.items():
                        dtypes[name] = str(data["dtypes"][col])
                    
                    if len(set(dtypes.values())) > 1:
                        schema_issues[col] = dtypes
                
                comparison["schema_compatibility"] = {
                    "compatible_columns": len(common_columns) - len(schema_issues),
                    "incompatible_columns": len(schema_issues),
                    "issues": schema_issues
                }
            
            logger.info(f"Compared {len(datasets)} datasets successfully")
            return comparison
            
        except Exception as e:
            error_msg = f"Failed to compare datasets: {e}"
            logger.error(error_msg)
            return {"status": "error", "message": str(e)}


# Convenience functions for the main API
def analyze_data_file(file_path: str, generate_viz: bool = True, 
                     report_format: str = "json") -> Dict[str, Any]:
    """
    Convenience function to analyze a data file and generate report.
    
    Args:
        file_path: Path to the data file
        generate_viz: Whether to generate visualizations
        report_format: Format for the report
        
    Returns:
        Dictionary with analysis and report results
    """
    analyzer = DataAnalyzer()
    
    try:
        # Perform analysis
        analysis_result = analyzer.analyze_csv(file_path, generate_viz)
        
        if analysis_result["status"] != "success":
            return analysis_result
        
        # Generate report
        report_result = analyzer.generate_report(analysis_result, report_format)
        
        return {
            "status": "success",
            "analysis": analysis_result,
            "report": report_result,
            "message": "Data analysis and report generation completed successfully"
        }
        
    except Exception as e:
        logger.error(f"Error in analyze_data_file: {e}")
        return {"status": "error", "message": str(e)}


def quick_data_summary(file_path: str) -> Dict[str, Any]:
    """
    Generate a quick summary of a data file.
    
    Args:
        file_path: Path to the data file
        
    Returns:
        Dictionary with quick summary
    """
    analyzer = DataAnalyzer()
    
    try:
        load_result = analyzer.load_data(file_path)
        
        if load_result["status"] != "success":
            return load_result
        
        df = pd.read_csv(file_path)  # Assuming CSV
        
        return {
            "status": "success",
            "file_name": os.path.basename(file_path),
            "shape": df.shape,
            "columns": df.columns.tolist(),
            "data_types": df.dtypes.to_dict(),
            "missing_values": df.isnull().sum().to_dict(),
            "sample_data": df.head(3).to_dict('records'),
            "summary_stats": df.describe().to_dict() if len(df.select_dtypes(include=[np.number]).columns) > 0 else {}
        }
        
    except Exception as e:
        logger.error(f"Error in quick_data_summary: {e}")
        return {"status": "error", "message": str(e)}
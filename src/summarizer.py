"""
Convert HTML pages to Markdown representations with metadata included at page bottom.
"""

# imports
import csv
import json
from pathlib import Path

# packages
import tqdm
from pydantic import BaseModel, Field
from alea_llm_client import BaseAIModel, OpenAIModel
from alea_llm_client.llms.prompts.sections import format_prompt


# constants
from config import DEFAULT_JSON_PATH, DEFAULT_SUMMARY_PATH, PROJECT_PATH


class Summary(BaseModel):
    summary: str = Field(..., description="Detailed summary of the document")
    eli5: str = Field(
        ..., description="One to two sentence summary in plain English for a child"
    )
    keywords: list[str] = Field(
        ..., description="Simple keywords or topics to categorize or label"
    )
    issues: list[str] = Field(
        ..., description="List of issues, concerns, or questions identified"
    )
    citations: list[str] = Field(
        ..., description="Cited laws, rules, or other key references"
    )
    document_type: str = Field(..., description="Type of document")


# get files from raw path
def get_files(json_path: Path = DEFAULT_JSON_PATH) -> list[Path]:
    """
    Get the list of files from the raw path.
    """
    return sorted([p for p in json_path.rglob("*.json") if p.is_file()])


def summarize_page(model: BaseAIModel, page_data: dict) -> dict:
    """
    Summarize the page data.

    Args:
        model: BaseAIModel, the AI model
        page_data: dict, the page data

    Returns:
        dict, the summarized page data
    """
    instructions = [
        "You are building a database of pages from the White House website.",
        "Read the TEXT of the page above.",
        "summary: First, summarize the text:\n"
        " - write 2-3 paragraphs in neutral, informative style\n"
        " - use third person and active voice\n"
        " - focus on the who, what, when, where, why, how\n"
        " - use Markdown to richly format your summary\n",
        "eli5: Second, simplify your summary into an ELI5:\n"
        " - write in plain English for a child\n"
        " - use Markdown for emphasis\n",
        "issues: Third, identify any issues, concerns, or questions you might have.",
        "citations: Fourth, identify any citations to laws, rules, or other authorities like USC, FR, CFR, PL, etc.",
        "keywords: Fifth, abstract your summary into a list of keywords or topics to use as search categories or labels.",
        "document_type: Sixth, identify the type of document: \n"
        " - Press Release\n"
        " - Fact Sheet\n"
        " - Presidential Action\n"
        " - Executive Order\n"
        " - Presidential Memorandum\n"
        " - Proclamation",
        "Output your response in JSON according to the SCHEMA below.",
    ]

    prompt = format_prompt(
        {
            "markdown": page_data.get("markdown", ""),
            "instructions": instructions,
            "schema": Summary,
        }
    )

    # get the folder name as the EO action
    response = model.json(prompt, system="Respond in JSON.", max_completion_tokens=8192)
    return response.data


if __name__ == "__main__":
    # set model
    model = OpenAIModel(model="gpt-4o")

    # build summary data
    summary_data = []

    # get files
    for json_path in tqdm.tqdm(get_files()):
        try:
            # read data
            page_data = json.loads(json_path.read_text(encoding="utf-8"))

            # check if "Page of" in og:title
            if "– Page" in page_data.get("og:title", ""):
                continue

            # summarize the page
            if "summary" not in page_data:
                print(f"Summarizing {json_path}...")
                summarized_page_data = summarize_page(model, page_data)

                # merge onto page_data and update json path
                page_data.update(summarized_page_data)

                # write it back out for review
                with open(json_path, "wt", encoding="utf-8") as output_file:
                    output_file.write(json.dumps(page_data, indent=2))

            # add to summary data or csv output
            summary_data.append(
                {
                    "title": page_data.get("og:title", page_data.get("title", None)),
                    "document_type": page_data.get("document_type", None),
                    "eli5": page_data.get("eli5", None),
                    "keywords": "; ".join(page_data.get("keywords", [])),
                    "url": page_data.get("og:url", None),
                }
            )

            # then write markdown summary to summary path
            output_summary_file = DEFAULT_SUMMARY_PATH / f"{json_path.stem}.md"
            output_summary_file.parent.mkdir(parents=True, exist_ok=True)
            output_summary_file.write_text(page_data["summary"], encoding="utf-8")
        except Exception as e:
            print(f"Error processing {json_path}: {e}")
            continue

    # output to pages.csv
    with open(
        PROJECT_PATH / "pages.csv", "wt", encoding="utf-8", newline=""
    ) as output_csv:
        writer = csv.DictWriter(
            output_csv,
            fieldnames=["title", "document_type", "eli5", "keywords", "url"],
            delimiter=",",
            quoting=csv.QUOTE_ALL,
        )
        writer.writeheader()
        writer.writerows(summary_data)

import pypdf
import os
import re

pdf_folder_path = "pdf"
md_template_path = "_template.md"


class OutlineNode:
    def __init__(self, name, pages_in_it=0) -> None:
        self.name = name
        self.pages_in_it = pages_in_it
        self.children = []


def create_outline(writer: pypdf.PdfWriter, root: OutlineNode):
    pc = 0

    def impl(root: OutlineNode, parent=None):
        nonlocal pc
        outline_parent = writer.add_outline_item(root.name, pc, parent)
        pc += root.pages_in_it

        for c in root.children:
            impl(c, outline_parent)

    impl(root)


def format_name(s: str):
    name = s.split("/")[-1].removesuffix(".pdf")
    return re.sub(r"^\d+-", "", name)


def format_md_link(s: str):
    depth = s.count("/") - pdf_folder_path.count("/") - 2
    link = s.removesuffix(".pdf") + ".pdf"
    li = "* " if depth >= 0 else "# "
    return " " * 4 * depth + f"{li}[{format_name(s)}]({link})\n"


class Merger:
    def __init__(self, folder: str) -> None:
        self.folder = folder
        self.md_title = format_name(folder)
        self.md_content = ""

    def merge(self):
        self._merge(self.folder)

    def _merge(self, dir):
        self.md_content += format_md_link(dir)
        root = OutlineNode(format_name(dir.split("/")[-1]))
        with pypdf.PdfWriter() as writer:
            for item in sorted(os.listdir(dir)):
                path = os.path.join(dir, item)
                if os.path.isdir(path):
                    root.children.append(self._merge(path))
                    writer.append_pages_from_reader(pypdf.PdfReader(path + ".pdf"))
                elif item.split(".")[-1] == "pdf":
                    self.md_content += format_md_link(path)
                    writer.append_pages_from_reader(pypdf.PdfReader(path))
                    root.children.append(
                        OutlineNode(format_name(item), len(pypdf.PdfReader(path).pages))
                    )

            create_outline(writer, root)
            with open(dir + ".pdf", "wb") as output:
                writer.write(output)

        return root

    def format_md(self, md_template: str):
        return md_template.replace("[title]", self.md_title, 1).replace(
            "[content]", self.md_content, 1
        )


with open(md_template_path, "r") as file:
    md_template = file.read()

for f in next(os.walk(pdf_folder_path))[1]:
    merger = Merger(os.path.join(pdf_folder_path, f))
    merger.merge()

    with open(os.path.join(f + ".md"), "w") as file:
        file.write(merger.format_md(md_template))

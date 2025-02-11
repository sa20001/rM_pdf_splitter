# rM_pdf_splitter

A Python utility to split continuous pages from reMarkable PDF exports into separate pages.

## Features

- Splits continuous pages.
- Maintains original quality.
- Simple (ugly) and lightweight interface.

## Simple (ugly) Interface
<p align="center">
  <img src="./assets/ui.png" alt="UI Preview" width="45%"> 
</p>

## Demo
<!-- <p align="center" style="display: flex; justify-content: center; align-items: flex-start;">
  <img id="img1" src="assets/rm_page.png" alt="before" style="height: auto;">
  <img id="img2" src="assets/cut_page.gif" alt="after" style="height: auto; max-height: 100vh;">
</p>

<style>
  #img1 {
    height: auto;
    max-height: 100%;
  }
  #img2 {
    height: auto;
    max-height: 100vh; /* Prevents it from being too large */
  }
</style> -->

<table align="center">
  <tr>
    <td align="center"><strong>Turn this:</strong></td>
    <td align="center"><strong>Into this:</strong></td>
  </tr>
  <tr>
    <td align="center"><img id="img1" src="assets/rm_page.png" alt="before"></td>
    <td align="center"><img id="img2" src="assets/cut_page.gif" alt="after"></td>
  </tr>
</table>

<script>
  window.onload = function() {
    let img1 = document.getElementById("img1");
    let img2 = document.getElementById("img2");

    img1.style.height = img2.clientHeight + "px"; // Match the GIF's height
    img1.style.width = "auto"; // Maintain aspect ratio
  };
</script>


## Automation with GitHub Actions

This project includes a GitHub Actions workflow to automatically bundle the Python code into an EXE file and upload it as a release.

## License

GPL License. See `LICENSE` for details.

